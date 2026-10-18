/** Static product preview for the hero: a mock browser window holding a question,
 *  a cited answer and its trace as slightly tilted, stacked cards. */
const TRACE_ROWS: [string, string, boolean?][] = [
  ["jev.analysis", "rewrite: no · safe"],
  ["retrieval", "568 ms · 15 candidates"],
  ["rerank · chunk_1", "0.92", true],
  ["generation", "1.69 s"],
];

const DOTS = ["bg-[#ff5f57]", "bg-[#febc2e]", "bg-[#28c840]"];

export function ProductPreview() {
  return (
    <figure
      aria-label="Example answer with its trace"
      className="overflow-hidden rounded-xl border-2 border-ink bg-card shadow-[8px_8px_0_var(--ink)]"
    >
      <div className="flex items-center gap-3 border-b-2 border-ink bg-secondary px-4 py-2.5">
        <span aria-hidden className="flex gap-1.5">
          {DOTS.map((c) => (
            <span key={c} className={`size-3 rounded-full border-[1.5px] border-ink ${c}`} />
          ))}
        </span>
        <span className="flex-1 truncate rounded-md border-2 border-ink bg-card px-3 py-0.5 text-center font-mono text-xs text-muted-foreground">
          rag-track / app
        </span>
      </div>
      <div className="grid gap-4 bg-background p-5 sm:p-6">
        <p className="ml-auto w-fit rotate-1 rounded-lg border-2 border-ink bg-primary px-3 py-2 text-sm font-medium text-primary-foreground shadow-[3px_3px_0_var(--ink)]">
          Who is Yogesh?
        </p>
        <div className="-rotate-1 rounded-lg border-2 border-ink bg-card p-3 text-sm leading-relaxed shadow-[3px_3px_0_var(--ink)]">
          Yogesh Chopade is an AI / GenAI Engineer focused on backend and ML systems.
          <div className="mt-2">
            <span className="rounded-full border-2 border-ink px-2 py-0.5 font-mono text-xs">
              YogeshChopade_2026.pdf · p.1
            </span>
          </div>
        </div>
        <dl className="ml-4 grid rotate-[0.6deg] gap-1 rounded-lg border-2 border-dashed border-ink bg-card p-3 font-mono text-xs">
          {TRACE_ROWS.map(([name, value, accent]) => (
            <div key={name} className="flex justify-between gap-4">
              <dt className="text-muted-foreground">{name}</dt>
              <dd className={accent ? "font-semibold text-highlight" : ""}>{value}</dd>
            </div>
          ))}
        </dl>
      </div>
    </figure>
  );
}
