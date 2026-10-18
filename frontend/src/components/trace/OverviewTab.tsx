import type { Trace } from "@/lib/types";
import { cn, formatMs } from "@/lib/utils";

const STAGES = ["decomposition", "rewrite", "retrieval", "generation"];

// Label, where the score lives, and the threshold the backend acts on (backend/app/services/jev.py)
const DECISIONS: { label: string; group: "jev_query_analysis" | "jev_answer_guard"; key: string; threshold: number }[] = [
  { label: "split", group: "jev_query_analysis", key: "multi_part", threshold: 0.5 },
  { label: "rewrite", group: "jev_query_analysis", key: "needs_rewrite", threshold: 0.5 },
  { label: "jailbreak", group: "jev_query_analysis", key: "jailbreak", threshold: 0.7 },
  { label: "harmful", group: "jev_query_analysis", key: "harmful_request", threshold: 0.7 },
  { label: "unsupported", group: "jev_answer_guard", key: "unsupported", threshold: 0.85 },
  { label: "harmful output", group: "jev_answer_guard", key: "harmful_output", threshold: 0.7 },
];

export function OverviewTab({ trace }: { trace: Trace }) {
  const stages = STAGES.filter((s) => s in trace.latency);
  const total = stages.reduce((sum, s) => sum + trace.latency[s], 0);
  const rewritten = !!trace.rewritten_query && trace.rewritten_query !== trace.original_query;

  const decisions = DECISIONS.flatMap((d) => {
    const score = trace.metadata?.[d.group]?.[d.key];
    return typeof score === "number" ? [{ ...d, score }] : [];
  });

  return (
    <div className="grid gap-6">
      <div className="grid gap-2">
        <div className="flex items-baseline justify-between text-sm">
          <h3 className="font-medium">Stage timings</h3>
          <span className="font-mono text-xs text-muted-foreground">total {formatMs(total)}</span>
        </div>
        <ul className="grid gap-2 font-mono text-xs">
          {stages.map((stage) => {
            const ms = trace.latency[stage];
            return (
              <li key={stage} className="grid grid-cols-[7.5rem_1fr_4.5rem] items-center gap-3">
                <span className="flex items-center gap-1.5 text-muted-foreground">
                  {stage}
                  {stage === "rewrite" && (
                    <span className="rounded border px-1 text-[10px]">{rewritten ? "rewritten" : "skipped"}</span>
                  )}
                </span>
                <span className="h-2 overflow-hidden rounded-full bg-muted" aria-hidden>
                  <span
                    className="block h-full rounded-full bg-primary"
                    style={{ width: `${total ? Math.max((ms / total) * 100, 1) : 0}%` }}
                  />
                </span>
                <span className="text-right">{formatMs(ms)}</span>
              </li>
            );
          })}
        </ul>
      </div>

      <div className="grid gap-2">
        <h3 className="text-sm font-medium">Jev decisions</h3>
        {decisions.length === 0 ? (
          <p className="text-sm text-muted-foreground">Not recorded</p>
        ) : (
          <ul aria-label="Jev decisions" className="flex flex-wrap gap-2">
            {decisions.map((d) => {
              const yes = d.score >= d.threshold;
              return (
                <li
                  key={d.label}
                  className={cn(
                    "rounded-md border px-2 py-1 font-mono text-xs",
                    yes && "border-primary/60 text-primary"
                  )}
                  title={`yes when ≥ ${d.threshold}`}
                >
                  {d.label} <strong className="font-semibold">{yes ? "yes" : "no"}</strong>{" "}
                  <span className="text-muted-foreground">{d.score.toFixed(2)}</span>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </div>
  );
}
