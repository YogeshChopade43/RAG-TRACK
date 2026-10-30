import type { ModelCall } from "@/lib/types";
import { cn, formatCost, formatMs, formatTokens } from "@/lib/utils";

const tokensOf = (c: ModelCall) =>
  c.prompt_tokens == null && c.completion_tokens == null ? null : (c.prompt_tokens ?? 0) + (c.completion_tokens ?? 0);

/** One bar per LLM / Jev call, placed on a shared time axis, with tokens and cost. */
export function CallTimeline({ calls }: { calls: ModelCall[] }) {
  const end = Math.max(...calls.map((c) => c.start_ms + c.duration_ms), 1);
  const tokens = calls.map(tokensOf).filter((t): t is number => t != null);
  const costs = calls.map((c) => c.cost_usd).filter((v): v is number => v != null);
  const jevCostMissing = calls.some((c) => c.kind === "jev" && c.cost_usd == null);
  const total = [
    tokens.length ? formatTokens(tokens.reduce((a, b) => a + b, 0)) : null,
    costs.length ? formatCost(costs.reduce((a, b) => a + b, 0)) + (jevCostMissing ? " excl. Jev" : "") : null,
  ].filter(Boolean);

  return (
    <div className="grid gap-2">
      <div className="flex items-baseline justify-between text-sm">
        <h3 className="font-medium">Model calls</h3>
        {total.length > 0 && <span className="font-mono text-xs text-muted-foreground">Total: {total.join(" · ")}</span>}
      </div>
      <ul aria-label="Model calls" className="grid gap-2 font-mono text-xs">
        {calls.map((c, i) => {
          const t = tokensOf(c);
          return (
            <li key={i} className="grid grid-cols-[7.5rem_1fr_auto] items-center gap-3" title={c.error ?? c.model}>
              <span className="flex items-center gap-1.5 truncate">
                <span
                  className={cn(
                    "rounded border px-1 text-[10px]",
                    c.kind === "jev" ? "border-ink bg-primary text-primary-foreground" : "text-muted-foreground"
                  )}
                >
                  {c.kind === "jev" ? "Jev" : "LLM"}
                </span>
                <span className={cn("truncate", !c.ok && "text-destructive line-through")}>{c.purpose}</span>
              </span>
              <span className="relative h-2 rounded-full bg-muted" aria-hidden>
                <span
                  className={cn("absolute inset-y-0 rounded-full", c.ok ? "bg-primary" : "bg-destructive")}
                  style={{
                    left: `${(c.start_ms / end) * 100}%`,
                    width: `${Math.max((c.duration_ms / end) * 100, 1)}%`,
                  }}
                />
              </span>
              <span className="flex justify-end gap-1.5 whitespace-nowrap">
                <span>{formatMs(c.duration_ms)}</span>
                {t != null && <span className="text-muted-foreground">{formatTokens(t)}</span>}
                {c.cost_usd != null && <span className="text-muted-foreground">{formatCost(c.cost_usd)}</span>}
              </span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
