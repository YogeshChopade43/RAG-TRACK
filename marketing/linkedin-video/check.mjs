// Assertions for the video: determinism, fonts, scene timing, layout bounds, output format.
// Exits non-zero if any check fails.
import { chromium } from "playwright";
import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import ffmpeg from "ffmpeg-static";
import { start } from "./serve.mjs";

const W = 1080, H = 1350, MARGIN = 48;
const results = [];
const check = (name, ok, detail = "") => results.push({ name, ok, detail });

const server = await start();
const browser = await chromium.launch({ channel: "chrome" });
const page = await browser.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: 1 });
await page.goto(server.url + "?render");
await page.evaluate(() => document.fonts.ready);

check("fonts", await page.evaluate(() => document.fonts.check('700 64px "Lexend Variable"')));

const shotAt = async (ms) => {
  await page.evaluate((t) => window.seek(t), ms);
  return page.screenshot({ type: "png" });
};
const a = await shotAt(20000);
await shotAt(5000);
const b = await shotAt(20000);
check("determinism", a.equals(b), "seek(20000) → seek(5000) → seek(20000) must match");

const { scenes, duration } = await page.evaluate(() => ({ scenes: window.SCENES, duration: window.DURATION }));
const contiguous = scenes[0].start === 0 && scenes.at(-1).end === duration && scenes.every((s, i) => i === 0 || s.start === scenes[i - 1].end);
check("scenes", contiguous, scenes.map((s) => `${s.id} ${s.start}-${s.end}`).join(", "));

for (const s of scenes) {
  const bad = await page.evaluate(
    ({ s, W, H, M }) => {
      window.seek(s.start + s.hold);
      return [...document.querySelectorAll(`#s-${s.id} [data-el]`)]
        .filter((el) => getComputedStyle(el).opacity !== "0")
        .map((el) => ({ el: el.dataset.el, r: el.getBoundingClientRect() }))
        .filter(({ r }) => r.left < M || r.top < M || r.right > W - M || r.bottom > H - M)
        .map(({ el, r }) => `${el} [${Math.round(r.left)},${Math.round(r.top)},${Math.round(r.right)},${Math.round(r.bottom)}]`);
    },
    { s, W, H, M: MARGIN }
  );
  check(`bounds:${s.id}`, bad.length === 0, bad.join("; "));
}

for (const [i, s] of scenes.entries()) {
  if (i === 0) continue;
  const op = await page.evaluate(
    ({ t, prev, cur }) => {
      window.seek(t);
      const o = (id) => Number(getComputedStyle(document.getElementById(`s-${id}`)).opacity);
      return [o(prev), o(cur)];
    },
    { t: s.start - 450, prev: scenes[i - 1].id, cur: s.id }
  );
  check(`boundary:${s.id}`, op[0] === 1 && op[1] === 0, `prev=${op[0]} cur=${op[1]}`);
}

// On-screen claims that must stay true to the code (this is posted publicly)
const text = (id) => page.evaluate((i) => document.getElementById(i).textContent.replace(/\s+/g, " "), id);
check("claim:trace-consistent", (await text("w-trace")).includes("rewrite: yes"), "fixture needs_rewrite = 0.78");
check("claim:old-safety", !(await text("g-before")).includes("No safety checks"), "old code had a regex input filter");
check("claim:reranker-weights", (await page.locator("#k-before .weights span").count()) === 5, "RerankingService had 5 weighted signals");
const pTitle = await text("p-head");
check("claim:pipeline", !pTitle.includes("per answer") && !pTitle.includes("calls"), "ingestion steps run once; split questions add a Jev call");

const overlaps = await page.evaluate(({ duration, ids }) => {
  const bad = [];
  for (let t = 0; t <= duration; t += 1000 / 30) {
    window.seek(t);
    const visible = ids.filter((id) => Number(getComputedStyle(document.getElementById(`s-${id}`)).opacity) > 0);
    if (visible.length > 1) bad.push(`${Math.round(t)}ms: ${visible.join("+")}`);
  }
  return bad;
}, { duration, ids: scenes.map((s) => s.id) });
check("no-overlap", overlaps.length === 0, overlaps.slice(0, 3).join("; "));

await browser.close();
server.close();

const mp4 = new URL("./out/rag-track-linkedin.mp4", import.meta.url);
if (process.argv.includes("--output")) {
  if (!existsSync(mp4)) check("output", false, "out/rag-track-linkedin.mp4 missing");
  else {
    const info = spawnSync(ffmpeg, ["-hide_banner", "-i", mp4.pathname.replace(/^\/([A-Za-z]:)/, "$1")], { encoding: "utf8" }).stderr;
    const want = ["Duration: 00:00:40.00", "1080x1350", "yuv420p", "30 fps", "h264"];
    const missing = want.filter((w) => !info.includes(w));
    if (info.includes("Audio:")) missing.push("unexpected audio stream");
    check("output", missing.length === 0, missing.length ? `missing: ${missing.join(", ")}` : info.match(/Stream.*Video.*/)?.[0] ?? "");
  }
}

for (const r of results) console.log(`${r.ok ? "PASS" : "FAIL"}  ${r.name}${r.detail ? "  — " + r.detail : ""}`);
process.exit(results.every((r) => r.ok) ? 0 : 1);
