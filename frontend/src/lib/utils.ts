export { cn } from "cn";

/** "568 ms" below one second, "1.69 s" from there on. */
export function formatMs(ms: number): string {
  return ms < 999.5 ? `${Math.round(ms)} ms` : `${(ms / 1000).toFixed(2)} s`;
}

/** "850 tokens" below a thousand, "1.9k tokens" from there on. */
export function formatTokens(n: number): string {
  return n < 1000 ? `${n} tokens` : `${(n / 1000).toFixed(1)}k tokens`;
}

/** "$0.0004", "$0.00007", "$1.2" (two significant digits); "<$0.00001" for dust. */
export function formatCost(usd: number): string {
  if (usd === 0) return "$0";
  if (usd < 0.00001) return "<$0.00001";
  return `$${Number(usd.toPrecision(2))}`;
}
