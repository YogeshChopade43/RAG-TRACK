/** Static product preview for the hero: a question, a cited answer and its trace. */
const TRACE_ROWS: [string, string, boolean?][] = [
  ["jev.analysis", "rewrite: no · safe"],
  ["retrieval", "568 ms · 15 candidates"],
  ["rerank · chunk_1", "0.92", true],
  ["generation", "1.69 s"],
];

export function ProductPreview() {
  return (
    <figure
      aria-label="Example answer with its trace"
      className="rounded-xl border bg-card p-4 shadow-2xl shadow-black/20 sm:p-5"
    >
      <p className="ml-auto w-fit rounded-xl bg-secondary px-3 py-2 text-sm">Who is Yogesh?</p>
      <div className="mt-3 rounded-xl border bg-background p-3 text-sm leading-relaxed">
        Yogesh Chopade is an AI / GenAI Engineer focused on backend and ML systems.
        <div className="mt-2">
          <span className="rounded-full border px-2 py-0.5 text-xs text-muted-foreground">
            YogeshChopade_2026.pdf · p.1
          </span>
        </div>
      </div>
      <dl className="mt-3 grid gap-1 border-t border-dashed pt-3 font-mono text-xs">
        {TRACE_ROWS.map(([name, value, accent]) => (
          <div key={name} className="flex justify-between gap-4">
            <dt className="text-muted-foreground">{name}</dt>
            <dd className={accent ? "font-semibold text-primary" : ""}>{value}</dd>
          </div>
        ))}
      </dl>
    </figure>
  );
}
