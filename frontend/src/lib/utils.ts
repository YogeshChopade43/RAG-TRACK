export { cn } from "cn";

/** "568 ms" below one second, "1.69 s" from there on. */
export function formatMs(ms: number): string {
  return ms < 999.5 ? `${Math.round(ms)} ms` : `${(ms / 1000).toFixed(2)} s`;
}
