// Renders index.html frame by frame into out/rag-track-linkedin.mp4 (+ out/poster.png).
//   node render.mjs              full 40 s video
//   node render.mjs --frames 60  first N frames only (quick test)
//   node render.mjs --stills     one PNG per scene at its hold time + out/contact-sheet.png
import { chromium } from "playwright";
import { spawn } from "node:child_process";
import { mkdirSync, writeFileSync } from "node:fs";
import ffmpeg from "ffmpeg-static";
import { start } from "./serve.mjs";

const W = 1080, H = 1350, FPS = 30;
const OUT = new URL("./out/", import.meta.url);
const outPath = (name) => new URL(name, OUT).pathname.replace(/^\/([A-Za-z]:)/, "$1");
mkdirSync(OUT, { recursive: true });

const args = process.argv.slice(2);
const server = await start();
const browser = await chromium.launch({ channel: "chrome" });
const page = await browser.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: 1 });
await page.goto(server.url + "?render");
await page.evaluate(() => document.fonts.ready);
const shot = async (ms, opts = {}) => {
  await page.evaluate((t) => window.seek(t), ms);
  return page.screenshot({ type: "png", ...opts });
};

try {
  if (args.includes("--stills")) {
    const scenes = await page.evaluate(() => window.SCENES);
    const files = [];
    for (const s of scenes) {
      const file = `still-${s.id}.png`;
      writeFileSync(outPath(file), await shot(s.start + s.hold));
      files.push(file);
    }
    // 4x2 contact sheet at half size
    const cells = files.map((f) => `<img src="${f}" style="width:540px;height:675px;display:block">`).join("");
    const sheet = await browser.newPage({ viewport: { width: 2160, height: 1350 } });
    await sheet.goto(server.url);
    await sheet.setContent(
      `<base href="${server.url}out/"><body style="margin:0;display:grid;grid-template-columns:repeat(4,540px)">${cells}</body>`
    );
    await sheet.waitForLoadState("networkidle");
    await sheet.screenshot({ path: outPath("contact-sheet.png") });
    console.log(`Wrote ${files.length} stills and contact-sheet.png`);
  } else {
    const duration = await page.evaluate(() => window.DURATION);
    const i = args.indexOf("--frames");
    const frames = i >= 0 ? Number(args[i + 1]) : Math.round((duration / 1000) * FPS);
    const enc = spawn(
      ffmpeg,
      ["-y", "-f", "image2pipe", "-framerate", String(FPS), "-i", "-",
       "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", "-preset", "slow",
       "-movflags", "+faststart", "-an", outPath("rag-track-linkedin.mp4")],
      { stdio: ["pipe", "ignore", "pipe"] }
    );
    let log = "";
    enc.stderr.on("data", (d) => (log = (log + d).slice(-4000)));
    const done = new Promise((res, rej) => enc.on("close", (c) => (c === 0 ? res() : rej(new Error(log)))));
    for (let f = 0; f < frames; f++) {
      const png = await shot((f * 1000) / FPS);
      if (!enc.stdin.write(png)) await new Promise((r) => enc.stdin.once("drain", r));
      if (f % 100 === 0) console.log(`frame ${f}/${frames}`);
    }
    enc.stdin.end();
    await done;
    writeFileSync(outPath("poster.png"), await shot(38500));
    console.log(`Wrote out/rag-track-linkedin.mp4 (${frames} frames) and out/poster.png`);
  }
} finally {
  await browser.close();
  server.close();
}
