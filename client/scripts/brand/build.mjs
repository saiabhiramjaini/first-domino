// Builds the raster brand assets from the SVG sources. Run from client/: bun scripts/brand/build.mjs
// Needs Google Chrome for the OG image (it renders scripts/brand/og.html with the Geist font).
import { execFileSync } from "node:child_process";
import { readFileSync, writeFileSync, mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

import sharp from "sharp";

const CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";

async function png(svgPath, size) {
  return sharp(readFileSync(svgPath), { density: 1200 }).resize(size, size).png().toBuffer();
}

// An .ico file may hold PNG images directly: a 6-byte header, one 16-byte entry per image, then the images.
function ico(images) {
  const header = Buffer.alloc(6 + 16 * images.length);
  header.writeUInt16LE(0, 0);
  header.writeUInt16LE(1, 2);
  header.writeUInt16LE(images.length, 4);
  let offset = header.length;
  images.forEach(({ size, data }, i) => {
    const at = 6 + 16 * i;
    header.writeUInt8(size >= 256 ? 0 : size, at);
    header.writeUInt8(size >= 256 ? 0 : size, at + 1);
    header.writeUInt16LE(1, at + 4);
    header.writeUInt16LE(32, at + 6);
    header.writeUInt32LE(data.length, at + 8);
    header.writeUInt32LE(offset, at + 12);
    offset += data.length;
  });
  return Buffer.concat([header, ...images.map((image) => image.data)]);
}

const favicon = await Promise.all(
  [16, 32, 48].map(async (size) => ({ size, data: await png("src/app/icon.svg", size) }))
);
writeFileSync("src/app/favicon.ico", ico(favicon));
writeFileSync("src/app/apple-icon.png", await png("public/brand/app-icon.svg", 180));
writeFileSync("public/icon-192.png", await png("public/brand/app-icon.svg", 192));
writeFileSync("public/icon-512.png", await png("public/brand/app-icon.svg", 512));

const work = mkdtempSync(join(tmpdir(), "fd-og-"));
try {
  const shot = join(work, "og.png");
  execFileSync(
    CHROME,
    [
      "--headless=new",
      "--disable-gpu",
      "--hide-scrollbars",
      "--force-device-scale-factor=1",
      "--virtual-time-budget=5000",
      `--user-data-dir=${join(work, "profile")}`,
      "--window-size=1200,630",
      `--screenshot=${shot}`,
      `file://${join(process.cwd(), "scripts/brand/og.html")}`,
    ],
    { stdio: "ignore" }
  );
  const og = await sharp(shot).resize(1200, 630).png().toBuffer();
  writeFileSync("src/app/opengraph-image.png", og);
  writeFileSync("src/app/twitter-image.png", og);
} finally {
  rmSync(work, { recursive: true, force: true });
}
process.stdout.write("brand assets written\n");
