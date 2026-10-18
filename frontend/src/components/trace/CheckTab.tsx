import { CheckCircle2, TriangleAlert } from "lucide-react";
import type { Trace } from "@/lib/types";
import { cn } from "@/lib/utils";

// Thresholds the backend acts on (backend/app/services/jev.py)
const CHECKS = [
  { key: "unsupported", label: "Unsupported claims", threshold: 0.85, action: "adds a warning to the answer" },
  { key: "harmful_output", label: "Harmful output", threshold: 0.7, action: "replaces the answer with a refusal" },
];

export function CheckTab({ trace }: { trace: Trace }) {
  const guard = trace.metadata?.jev_answer_guard;
  if (!guard) return <p className="text-sm text-muted-foreground">Not recorded</p>;

  const flagged = CHECKS.some((c) => (guard[c.key] ?? 0) >= c.threshold);

  return (
    <div className="grid gap-5">
      <p className={cn("flex items-center gap-2 text-sm font-medium", flagged ? "text-destructive" : "text-success")}>
        {flagged ? <TriangleAlert aria-hidden className="size-4" /> : <CheckCircle2 aria-hidden className="size-4" />}
        {flagged ? "Flagged" : "No issues found"}
      </p>
      <ul className="grid gap-4">
        {CHECKS.map((c) => {
          const score = guard[c.key];
          return (
            <li key={c.key} className="grid gap-1.5">
              <div className="flex items-baseline justify-between text-sm">
                <span>{c.label}</span>
                <span className="font-mono text-xs">{typeof score === "number" ? score.toFixed(2) : "–"}</span>
              </div>
              <div
                role="meter"
                aria-label={c.label}
                aria-valuemin={0}
                aria-valuemax={1}
                aria-valuenow={score ?? 0}
                className="relative h-2 rounded-full bg-muted"
              >
                <span
                  className={cn("block h-full rounded-full", (score ?? 0) >= c.threshold ? "bg-destructive" : "bg-primary")}
                  style={{ width: `${Math.min((score ?? 0) * 100, 100)}%` }}
                />
                <span
                  aria-hidden
                  className="absolute -top-1 h-4 w-px bg-foreground/60"
                  style={{ left: `${c.threshold * 100}%` }}
                />
              </div>
              <p className="text-xs text-muted-foreground">
                threshold {c.threshold} — above it the backend {c.action}
              </p>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
