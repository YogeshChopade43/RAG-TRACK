import { ArrowRight } from "lucide-react";
import { cn } from "@/lib/utils";

const STEPS: { name: string; jev?: boolean }[] = [
  { name: "Upload" },
  { name: "Chunk" },
  { name: "FAISS + BM25" },
  { name: "Question" },
  { name: "Jev analysis", jev: true },
  { name: "Hybrid search" },
  { name: "Jev rerank", jev: true },
  { name: "LLM answer" },
  { name: "Jev guard", jev: true },
];

export function Pipeline() {
  return (
    <section aria-labelledby="how-heading" className="border-t-2 border-ink">
      <div className="mx-auto max-w-6xl px-4 py-20 sm:px-6">
        <p className="font-mono text-xs font-semibold tracking-widest text-highlight uppercase">Pipeline</p>
        <h2 id="how-heading" className="mt-2 text-3xl font-bold tracking-tight sm:text-4xl">
          How it <span className="marker">works</span>
        </h2>
        <p className="mt-3 text-muted-foreground">Every answer passes the same observable pipeline.</p>
        <ol aria-label="RAG pipeline" className="mt-10 flex flex-wrap items-center gap-y-4">
          {STEPS.map((step, i) => (
            // The arrow lives inside the following step so a wrapped row never ends with one
            <li key={step.name} className="flex items-center">
              {i > 0 && <ArrowRight aria-hidden className="mx-1.5 size-4 shrink-0" />}
              <span
                className={cn(
                  "rounded-md border-2 border-ink bg-card px-3 py-1.5 font-mono text-sm font-medium shadow-[2px_2px_0_var(--ink)]",
                  step.jev && "bg-primary text-primary-foreground"
                )}
              >
                {step.name}
              </span>
            </li>
          ))}
        </ol>
        <p className="mt-6 flex items-center gap-2 text-sm text-muted-foreground">
          <span aria-hidden className="inline-block size-3 rounded-sm border-2 border-ink bg-primary" />
          Yellow steps are decisions made by the Jev decision model.
        </p>
      </div>
    </section>
  );
}
