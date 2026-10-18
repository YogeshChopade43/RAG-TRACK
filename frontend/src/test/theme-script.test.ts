// public/theme.js runs before the app bundle so the first paint already has the
// right theme (no light flash for users who chose dark).
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const script = readFileSync(resolve(__dirname, "../../public/theme.js"), "utf-8");

function run(opts: { stored?: string; prefersDark?: boolean }) {
  document.documentElement.className = "";
  localStorage.clear();
  if (opts.stored) localStorage.setItem("theme", opts.stored);
  window.matchMedia = vi.fn().mockReturnValue({ matches: !!opts.prefersDark }) as unknown as typeof window.matchMedia;
  new Function(script)();
  return document.documentElement.classList.contains("dark");
}

test("a saved dark theme adds the dark class before the app loads", () => {
  expect(run({ stored: "dark" })).toBe(true);
});

test("a saved light theme stays light", () => {
  expect(run({ stored: "light", prefersDark: true })).toBe(false);
});

test("no saved theme is light (the default), whatever the OS prefers", () => {
  expect(run({ prefersDark: true })).toBe(false);
});
