import { useState } from "react";
import type { Candidate } from "@/lib/types";
import { cn } from "@/lib/utils";

const PREVIEW_CHARS = 160;
const FILTERS = ["All", "Kept", "Dropped"] as const;
const REASONS: Record<string, string> = { below_min_relevance: "below relevance bar", beyond_top_k: "past top-k" };

const score = (label: string, v: number | null) => (
  <span>
    <span className="text-muted-foreground">{label} </span>
    {v == null ? "–" : v.toFixed(2)}
  </span>
);

function Row({ c, showFoundBy }: { c: Candidate; showFoundBy: boolean }) {
  const [open, setOpen] = useState(false);
  const long = c.content.length > PREVIEW_CHARS;
  const kept = c.status === "kept";
  return (
    <li className={cn("rounded-lg border p-3", !kept && "bg-muted/40")}>
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 font-mono text-xs">
        <span
          className={cn(
            "rounded-full border px-2 py-0.5 text-[11px] font-semibold",
            kept ? "border-ink bg-primary text-primary-foreground" : "text-muted-foreground",
          )}
        >
          {kept ? "kept" : "dropped"}
        </span>
        {c.reason && <span className="text-highlight">{REASONS[c.reason] ?? c.reason}</span>}
        <span>
          <span className="text-muted-foreground">jev </span>
          <span className="font-semibold">{c.jev == null ? "–" : c.jev.toFixed(2)}</span>
        </span>
        {score("fused", c.fused)}
        {score("vector", c.vector)}
        {score("bm25", c.bm25)}
        {c.ocr && (
          <span
            title="Text read from an image by OCR"
            className="rounded-full border px-2 py-0.5 text-[11px] font-semibold"
          >
            OCR
          </span>
        )}
        <span className="ml-auto text-muted-foreground">
          {[c.file_name, c.page_number != null ? `p.${c.page_number}` : null].filter(Boolean).join(" · ")}
        </span>
      </div>
      {showFoundBy && (
        <p className="mt-1 font-mono text-[11px] text-muted-foreground">found by: {c.found_by.join(" | ")}</p>
      )}
      <p className="mt-2 text-sm leading-relaxed break-words whitespace-pre-wrap">
        {open || !long ? c.content : `${c.content.slice(0, PREVIEW_CHARS).trimEnd()}…`}
      </p>
      {long && (
        <button
          type="button"
          aria-expanded={open}
          onClick={() => setOpen((o) => !o)}
          className="mt-1 text-xs text-highlight underline-offset-4 hover:underline focus-visible:outline-2 focus-visible:outline-ring"
        >
          {open ? "Show less" : "Show more"}
        </button>
      )}
    </li>
  );
}

/** Every chunk retrieval found, with its scores and why it did or didn't reach the model. */
export function CandidateList({ candidates, multipleQueries }: { candidates: Candidate[]; multipleQueries: boolean }) {
  const [filter, setFilter] = useState<(typeof FILTERS)[number]>("All");
  const keptCount = candidates.filter((c) => c.status === "kept").length;
  const shown = candidates.filter(
    (c) => filter === "All" || (filter === "Kept" ? c.status === "kept" : c.status === "dropped"),
  );

  return (
    <div className="grid gap-2">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-sm font-medium">{`${candidates.length} found → ${keptCount} kept`}</h3>
        <div className="flex gap-1" role="group" aria-label="Filter candidates">
          {FILTERS.map((f) => (
            <button
              key={f}
              type="button"
              aria-pressed={filter === f}
              onClick={() => setFilter(f)}
              className={cn(
                "rounded-md border px-2 py-0.5 text-xs focus-visible:outline-2 focus-visible:outline-ring",
                filter === f ? "border-ink bg-primary font-semibold text-primary-foreground" : "text-muted-foreground",
              )}
            >
              {f}
            </button>
          ))}
        </div>
      </div>
      <ol aria-label="Candidates" className="grid gap-2">
        {shown.map((c) => (
          <Row key={c.chunk_id} c={c} showFoundBy={multipleQueries} />
        ))}
      </ol>
    </div>
  );
}
