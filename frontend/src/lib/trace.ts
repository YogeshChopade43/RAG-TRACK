import type { Trace, TraceChunk } from "@/lib/types";

/** Reranked chunks when Jev ran, otherwise what retrieval returned. */
export function rankedChunks(trace: Trace): TraceChunk[] {
  return trace.reranked_chunks.length ? trace.reranked_chunks : trace.retrieved_chunks;
}

// Decision sources that mean Jev didn't decide (backend/app/api/retrieve.py FALLBACK_SOURCES)
const FALLBACK_SOURCES = new Set(["heuristic", "fusion", "unavailable"]);

/** Decisions the built-in rules made because Jev was unavailable. */
export function fallbackDecisions(trace: Trace): string[] {
  return Object.entries(trace.decision_sources ?? {})
    .filter(([, source]) => FALLBACK_SOURCES.has(source))
    .map(([name]) => name);
}
