import type { Usage } from "@/lib/types";
import { formatCost, formatTokens } from "@/lib/utils";

const badge = "rounded-full border px-2 py-0.5 font-mono text-[11px] leading-none";

/** Quiet footer facts about one answer: what it cost, and whether it was reused or ran on fallbacks. */
export function AnswerMeta(props: { usage?: Usage | null; cached?: boolean; fallbacks?: string[] }) {
  const { usage, cached, fallbacks = [] } = props;
  const parts: string[] = [];
  // A cached answer made no new calls: its zero usage would only be noise
  if (usage && !cached) {
    if (usage.total_tokens != null) parts.push(formatTokens(usage.total_tokens));
    if (usage.cost_usd != null) parts.push(formatCost(usage.cost_usd) + (usage.jev_cost_included ? "" : " excl. Jev"));
  }
  if (!parts.length && !cached && !fallbacks.length) return null;

  return (
    <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
      {parts.length > 0 && <span className="font-mono">{parts.join(" · ")}</span>}
      {cached && (
        <span className={badge} title="Reused an earlier answer to the same question: no new model calls">
          cached
        </span>
      )}
      {fallbacks.length > 0 && (
        <span
          className={`${badge} border-highlight/60 text-highlight`}
          title="Jev was unavailable for these decisions, so the built-in rules made them"
        >
          Jev fallback: {fallbacks.join(", ")}
        </span>
      )}
    </div>
  );
}
