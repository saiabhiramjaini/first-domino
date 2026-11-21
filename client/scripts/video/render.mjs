// Renders scripts/video/scene.html to an mp4, one exact frame at a time.
// Run from client/: bun scripts/video/render.mjs [output.mp4]
// To check the layout first: bun scripts/video/render.mjs --stills <folder> 2 6 13 (seconds).
// Needs Google Chrome and ffmpeg, and out/timing.js from voice.mjs. Chrome is driven over its DevTools protocol, so nothing
// is installed: the page's window.seek(seconds) draws each frame, then Chrome screenshots it.
import { spawn, execFileSync } from "node:child_process";
import { existsSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";

const CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const FPS = 30;
const WIDTH = 1920;
const HEIGHT = 1080;
const PORT = 9333;
const VOICE = resolve("scripts/video/out/narration.wav");
const stills = process.argv[2] === "--stills";
const output = resolve((stills ? process.argv[3] : process.argv[2]) ?? "first-domino-launch.mp4");
const stillTimes = stills ? process.argv.slice(4).map(Number) : [];

const work = mkdtempSync(join(tmpdir(), "fd-video-"));
const chrome = spawn(
  CHROME,
  [
    "--headless=new",
    "--disable-gpu",
    "--hide-scrollbars",
    "--force-device-scale-factor=1",
    `--remote-debugging-port=${PORT}`,
    `--user-data-dir=${join(work, "profile")}`,
    `--window-size=${WIDTH},${HEIGHT}`,
    `file://${resolve("scripts/video/scene.html")}`,
  ],
  { stdio: "ignore" }
);

async function pageSocketUrl() {
  for (let attempt = 0; attempt < 50; attempt++) {
    try {
      const targets = await (await fetch(`http://127.0.0.1:${PORT}/json`)).json();
      const page = targets.find((target) => target.type === "page");
      if (page) return page.webSocketDebuggerUrl;
    } catch {
      // Chrome is still starting.
    }
    await new Promise((done) => setTimeout(done, 200));
  }
  throw new Error("Chrome did not start");
}

const socket = new WebSocket(await pageSocketUrl());
await new Promise((done) => socket.addEventListener("open", done, { once: true }));
let nextId = 0;
const pending = new Map();
socket.addEventListener("message", (event) => {
  const message = JSON.parse(event.data);
  const waiter = pending.get(message.id);
  if (!waiter) return;
  pending.delete(message.id);
  if (message.error) waiter.reject(new Error(message.error.message));
  else waiter.resolve(message.result);
});
function send(method, params = {}) {
  const id = ++nextId;
  socket.send(JSON.stringify({ id, method, params }));
  return new Promise((resolve, reject) => pending.set(id, { resolve, reject }));
}
async function evaluate(expression) {
  const { result, exceptionDetails } = await send("Runtime.evaluate", {
    expression,
    awaitPromise: true,
    returnByValue: true,
  });
  if (exceptionDetails) throw new Error(exceptionDetails.text);
  return result.value;
}

async function capture(seconds) {
  await evaluate(`window.seek(${seconds})`);
  const { data } = await send("Page.captureScreenshot", {
    format: "png",
    clip: { x: 0, y: 0, width: WIDTH, height: HEIGHT, scale: 1 },
  });
  return Buffer.from(data, "base64");
}

try {
  await send("Emulation.setDeviceMetricsOverride", {
    width: WIDTH,
    height: HEIGHT,
    deviceScaleFactor: 1,
    mobile: false,
  });
  for (let attempt = 0; attempt < 50; attempt++) {
    if (await evaluate("typeof window.ready !== 'undefined'")) break;
    await new Promise((done) => setTimeout(done, 200));
  }
  await evaluate("window.ready");
  if (stills) {
    for (const seconds of stillTimes) {
      writeFileSync(join(output, `still_${seconds}s.png`), await capture(seconds));
    }
    console.log(`Wrote ${stillTimes.length} stills to ${output}`);
  } else {
    await renderVideo();
  }
} finally {
  socket.close();
  chrome.kill();
  rmSync(work, { recursive: true, force: true });
}

async function renderVideo() {
  const duration = await evaluate("window.DURATION");
  const frames = Math.round(duration * FPS);
  for (let frame = 0; frame < frames; frame++) {
    writeFileSync(
      join(work, `f_${String(frame).padStart(4, "0")}.png`),
      await capture(frame / FPS)
    );
    if (frame % FPS === 0) process.stdout.write(`\r${frame / FPS}s of ${duration}s`);
  }
  process.stdout.write("\n");
  execFileSync(
    "ffmpeg",
    [
      "-v",
      "error",
      "-y",
      "-framerate",
      String(FPS),
      "-i",
      join(work, "f_%04d.png"),
      // The voiceover from voice.mjs, when it has been made.
      ...(existsSync(VOICE) ? ["-i", VOICE, "-c:a", "aac", "-b:a", "192k", "-shortest"] : []),
      "-c:v",
      "libx264",
      "-pix_fmt",
      "yuv420p",
      "-crf",
      "18",
      "-preset",
      "slow",
      "-movflags",
      "+faststart",
      output,
    ],
    { stdio: "inherit" }
  );
  console.log(`Wrote ${output}`);
}
