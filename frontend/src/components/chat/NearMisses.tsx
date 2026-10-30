import type { NearMiss } from "@/lib/types";

/** For a "not found" answer: the passages that came closest, so the user can see whether
 *  the document lacks the answer or retrieval/ranking missed it. */
export function NearMisses({ items }: { items: NearMiss[] }) {
  if (!items.length) return null;
  const noneRelevant = items.every((m) => m.reason === "below_min_relevance");
  return (
    <section className="mt-3 rounded-lg border border-dashed p-3">
      <h3 className="text-sm font-semibold">Closest passages</h3>
      {noneRelevant && (
        <p className="mt-0.5 text-xs text-muted-foreground">
          The search found these, but none were judged relevant enough to use.
        </p>
      )}
      <ul aria-label="Closest passages" className="mt-2 grid gap-2">
        {items.map((m, i) => (
          <li key={i} className="grid grid-cols-[auto_auto_1fr] items-baseline gap-x-3 text-sm">
            <span className="font-mono text-xs text-muted-foreground">
              {m.page_number != null ? `p.${m.page_number}` : (m.file_name ?? "")}
            </span>
            <span className="font-mono text-xs font-semibold text-highlight">
              {m.jev != null ? m.jev.toFixed(2) : "—"}
            </span>
            <span className="truncate text-muted-foreground" title={m.preview}>
              {m.preview}
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}
