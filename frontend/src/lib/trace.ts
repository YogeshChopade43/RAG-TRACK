import type { Trace, TraceChunk } from "@/lib/types";

/** Reranked chunks when Jev ran, otherwise what retrieval returned. */
export function rankedChunks(trace: Trace): TraceChunk[] {
  return trace.reranked_chunks.length ? trace.reranked_chunks : trace.retrieved_chunks;
}
