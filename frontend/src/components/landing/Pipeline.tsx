import { ChevronRight } from "lucide-react";
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
    <section aria-labelledby="how-heading" className="border-t">
      <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6">
        <h2 id="how-heading" className="text-2xl font-semibold tracking-tight">
          How it works
        </h2>
        <p className="mt-2 text-muted-foreground">Every answer passes the same observable pipeline.</p>
        <ol aria-label="RAG pipeline" className="mt-8 flex flex-wrap items-center gap-y-3">
          {STEPS.map((step, i) => (
            // The arrow lives inside the following step so a wrapped row never ends with one
            <li key={step.name} className="flex items-center">
              {i > 0 && <ChevronRight aria-hidden className="mx-1 size-4 shrink-0 text-muted-foreground" />}
              <span
                className={cn(
                  "rounded-md border bg-card px-3 py-1.5 font-mono text-sm",
                  step.jev && "border-primary/60 text-primary"
                )}
              >
                {step.name}
              </span>
            </li>
          ))}
        </ol>
        <p className="mt-4 text-sm text-muted-foreground">
          <span className="text-primary">Highlighted</span> steps are decisions made by the Jev decision model.
        </p>
      </div>
    </section>
  );
}
