// Turns scripts/video/narration.json into the voiceover and the timings the scene follows.
// Run from client/ with OPENAI_API_KEY set: bun scripts/video/voice.mjs
// Writes scripts/video/out/<segment>.wav (cached: delete one to redo it), out/narration.wav
// and out/timing.js, which scene.html loads.
import { execFileSync } from "node:child_process";
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";

const DIR = "scripts/video";
const OUT = join(DIR, "out");
const MODEL = "gpt-4o-mini-tts";
const LEAD_IN = 0.8; // silence before the first line
const GAP = 0.45; // between lines
const PAUSES = { answer: 0.9, record: 0.9 }; // extra silence before these lines
const TAIL = 2.8; // after the last line, for the end card

const narration = JSON.parse(readFileSync(join(DIR, "narration.json"), "utf8"));
mkdirSync(OUT, { recursive: true });

async function speak(segment, file) {
  if (existsSync(file)) return;
  const key = process.env.OPENAI_API_KEY;
  if (!key) throw new Error("Set OPENAI_API_KEY to generate the voiceover");
  const response = await fetch("https://api.openai.com/v1/audio/speech", {
    method: "POST",
    headers: { Authorization: `Bearer ${key}`, "Content-Type": "application/json" },
    body: JSON.stringify({
      model: MODEL,
      voice: narration.voice,
      instructions: narration.instructions,
      input: segment.text,
      response_format: "wav",
    }),
  });
  if (!response.ok) throw new Error(`Speech failed for ${segment.id}: ${response.status}`);
  writeFileSync(file, Buffer.from(await response.arrayBuffer()));
  process.stdout.write(`voiced ${segment.id}\n`);
}

// Speech models leave half a second of silence around a line and long pauses inside it.
// Trim the edges, cap pauses, and speak a little faster, keeping the pitch.
const TIGHTEN = [
  "silenceremove=start_periods=1:start_threshold=-45dB:stop_periods=-1:stop_duration=0.25:stop_silence=0.25:stop_threshold=-45dB",
  "areverse",
  "silenceremove=start_periods=1:start_threshold=-45dB",
  "areverse",
  "atempo=1.06",
].join(",");

function tighten(file, tight) {
  execFileSync("ffmpeg", ["-v", "error", "-y", "-i", file, "-af", TIGHTEN, tight]);
}

function seconds(file) {
  const out = execFileSync("ffprobe", [
    "-v",
    "error",
    "-show_entries",
    "format=duration",
    "-of",
    "csv=p=0",
    file,
  ]);
  return Number(String(out).trim());
}

let cursor = LEAD_IN;
const segments = [];
for (const segment of narration.segments) {
  const raw = join(OUT, `${segment.id}.wav`);
  await speak(segment, raw);
  const file = join(OUT, `${segment.id}.tight.wav`);
  tighten(raw, file);
  cursor += PAUSES[segment.id] ?? 0;
  const length = seconds(file);
  segments.push({ id: segment.id, text: segment.text, file, start: cursor, end: cursor + length });
  cursor += length + GAP;
}
const total = Math.ceil((segments.at(-1).end + TAIL) * 10) / 10;

// One track: each line delayed to its start, mixed, brought to speech loudness (-16 LUFS),
// padded to the full length.
const inputs = segments.flatMap((s) => ["-i", s.file]);
const delays = segments
  .map((s, i) => `[${i}]adelay=${Math.round(s.start * 1000)}:all=1[a${i}]`)
  .join(";");
const mix = `${segments.map((_, i) => `[a${i}]`).join("")}amix=inputs=${segments.length}:normalize=0,loudnorm=I=-16:TP=-1.5:LRA=11,apad[out]`;
execFileSync("ffmpeg", [
  "-v",
  "error",
  "-y",
  ...inputs,
  "-filter_complex",
  `${delays};${mix}`,
  "-map",
  "[out]",
  "-t",
  String(total),
  "-ar",
  "48000",
  join(OUT, "narration.wav"),
]);

const timing = {
  total,
  segments: segments.map(({ id, text, start, end }) => ({ id, text, start, end })),
};
writeFileSync(join(OUT, "timing.js"), `window.TIMING = ${JSON.stringify(timing, null, 2)};\n`);
process.stdout.write(
  `narration ${total}s: ${segments.map((s) => `${s.id}@${s.start.toFixed(1)}`).join(" ")}\n`
);
