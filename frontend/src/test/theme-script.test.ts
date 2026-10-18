// public/theme.js runs before the app bundle so the first paint already has the
// right theme (no dark flash for light-theme users).
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const script = readFileSync(resolve(__dirname, "../../public/theme.js"), "utf-8");

function run(opts: { stored?: string; prefersLight?: boolean }) {
  document.documentElement.className = "dark"; // what index.html ships with
  if (opts.stored) localStorage.setItem("theme", opts.stored);
  window.matchMedia = vi.fn().mockReturnValue({ matches: !!opts.prefersLight }) as unknown as typeof window.matchMedia;
  new Function(script)();
  return document.documentElement.classList.contains("dark");
}

test("a saved light theme removes the dark class before the app loads", () => {
  expect(run({ stored: "light" })).toBe(false);
});

test("a saved dark theme stays dark even if the OS prefers light", () => {
  expect(run({ stored: "dark", prefersLight: true })).toBe(true);
});

test("no saved theme follows a light OS preference", () => {
  expect(run({ prefersLight: true })).toBe(false);
});

test("no saved theme and no light preference stays dark (the default)", () => {
  expect(run({})).toBe(true);
});
