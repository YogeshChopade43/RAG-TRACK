// Shapes returned by the FastAPI backend (backend/app/api/*.py and the trace model).

export type Tokens = { access_token: string; refresh_token: string; token_type: string };

export type User = { id: string; email: string; full_name: string | null; is_active: boolean };

export type Source = { file_name: string; page_number: number | null };

export type IngestResponse = { filename: string; document_id: string; status: string; message?: string | null };

export type QueryResponse = { trace_id: string; question: string; answer: string; sources: Source[] };

export type ApiKeyTest = { valid: boolean; message: string; model?: string | null };

export type TraceChunk = {
  chunk_id: string;
  content: string;
  score: number;
  metadata: Record<string, unknown>;
  rank?: number;
  final_score?: number;
  original_score?: number | null;
  llm_relevance_score?: number | null;
};

export type Trace = {
  trace_id: string;
  timestamp: string;
  original_query: string;
  rewritten_query: string | null;
  decomposed_queries: string[];
  retrieved_chunks: TraceChunk[];
  bm25_results: TraceChunk[];
  fusion_details: Record<string, unknown> | null;
  reranked_chunks: TraceChunk[];
  final_context: string | null;
  llm_response: string | null;
  llm_provider: string | null;
  llm_model: string | null;
  llm_temperature: number | null;
  llm_max_tokens: number | null;
  llm_timeout_seconds: number | null;
  latency: Record<string, number>;
  error: string | null;
  metadata?: {
    jev_query_analysis?: Record<string, number>;
    jev_answer_guard?: Record<string, number>;
  };
};
