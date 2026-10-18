import { useState } from "react";
import { rankedChunks } from "@/lib/trace";
import type { Trace, TraceChunk } from "@/lib/types";

const PREVIEW_CHARS = 160;

function ChunkCard({ chunk, rank, reranked }: { chunk: TraceChunk; rank: number; reranked: boolean }) {
  const [open, setOpen] = useState(false);
  const long = chunk.content.length > PREVIEW_CHARS;
  const meta = chunk.metadata as { file_name?: string; page_number?: number | null };
  const where = [meta.file_name, meta.page_number ? `p.${meta.page_number}` : null].filter(Boolean).join(" · ");

  return (
    <li className="rounded-lg border p-3">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 font-mono text-xs">
        <span className="text-muted-foreground">#{rank}</span>
        <span>
          {/* Without Jev reranking, `score` is the hybrid retrieval score */}
          <span className="text-muted-foreground">{reranked ? "jev " : "retrieval score "}</span>
          <span className="font-semibold text-highlight">{chunk.score.toFixed(2)}</span>
        </span>
        {typeof chunk.original_score === "number" && (
          <span>
            <span className="text-muted-foreground">fusion </span>
            <span>{chunk.original_score.toFixed(2)}</span>
          </span>
        )}
        {where && <span className="ml-auto text-muted-foreground">{where}</span>}
      </div>
      <p className="mt-2 text-sm leading-relaxed break-words whitespace-pre-wrap">
        {open || !long ? chunk.content : `${chunk.content.slice(0, PREVIEW_CHARS).trimEnd()}…`}
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

export function RetrievalTab({ trace }: { trace: Trace }) {
  const chunks = rankedChunks(trace);
  const fusion = trace.fusion_details as
    | { vector_count?: number; bm25_count?: number; fused_count?: number; fusion_weights?: Record<string, number> }
    | null;
  const subQueries = trace.decomposed_queries.filter((q) => q !== trace.original_query);
  const rewritten = trace.rewritten_query && trace.rewritten_query !== trace.original_query ? trace.rewritten_query : null;

  return (
    <div className="grid gap-5">
      <dl className="grid gap-1.5 text-sm sm:grid-cols-[8rem_1fr]">
        <dt className="text-muted-foreground">Question</dt>
        <dd>{trace.original_query}</dd>
        {rewritten && (
          <>
            <dt className="text-muted-foreground">Rewritten</dt>
            <dd className="font-mono text-xs leading-5">{rewritten}</dd>
          </>
        )}
        {subQueries.length > 0 && (
          <>
            <dt className="text-muted-foreground">Sub-questions</dt>
            <dd>
              <ul className="list-disc pl-4">
                {subQueries.map((q) => (
                  <li key={q}>{q}</li>
                ))}
              </ul>
            </dd>
          </>
        )}
        {fusion && (
          <>
            <dt className="text-muted-foreground">Hybrid search</dt>
            <dd className="font-mono text-xs leading-5">
              vector {fusion.vector_count ?? "–"} · bm25 {fusion.bm25_count ?? "–"} · fused {fusion.fused_count ?? "–"}
              {fusion.fusion_weights &&
                ` · weights ${Object.entries(fusion.fusion_weights)
                  .map(([k, w]) => `${k} ${w}`)
                  .join(" / ")}`}
            </dd>
          </>
        )}
      </dl>

      <div className="grid gap-2">
        <h3 className="text-sm font-medium">
          Chunks sent to the model <span className="text-muted-foreground">({chunks.length})</span>
        </h3>
        {chunks.length === 0 ? (
          <p className="text-sm text-muted-foreground">No chunks were retrieved.</p>
        ) : (
          <ol className="grid gap-2">
            {chunks.map((c, i) => (
              <ChunkCard key={c.chunk_id} chunk={c} rank={c.rank ?? i + 1} reranked={trace.reranked_chunks.length > 0} />
            ))}
          </ol>
        )}
      </div>
    </div>
  );
}
