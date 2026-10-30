// Shapes returned by the FastAPI backend (backend/app/api/*.py and the trace model).

export type Tokens = { access_token: string; refresh_token: string; token_type: string };

export type User = { id: string; email: string; full_name: string | null; is_active: boolean };

export type Source = { file_name: string; page_number: number | null };

export type IngestResponse = { filename: string; document_id: string; status: string; message?: string | null };

export type IngestStage = "queued" | "parsing" | "chunking" | "embedding" | "ready" | "failed";

export type IngestStatus = { document_id: string; status: IngestStage; error: string | null; pages: number | null };

export type Usage = { total_tokens: number | null; cost_usd: number | null; jev_cost_included: boolean };

export type DropReason = "below_min_relevance" | "beyond_top_k";

export type NearMiss = {
  file_name: string | null;
  page_number: number | null;
  jev: number | null;
  reason: DropReason | null;
  preview: string;
};

export type AnswerStatus = "answered" | "not_found" | "error";

// The transparency fields are optional: older backends don't send them
export type QueryResponse = {
  trace_id: string;
  question: string;
  answer: string;
  sources: Source[];
  cached?: boolean;
  answer_status?: AnswerStatus;
  usage?: Usage | null;
  near_misses?: NearMiss[];
  fallbacks?: string[];
};

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
  // Transparency fields (absent in older traces)
  candidates?: Candidate[] | null;
  expanded_queries?: string[] | null;
  calls?: ModelCall[] | null;
  decision_sources?: Record<string, string> | null;
  answer_status?: AnswerStatus | null;
  settings_used?: { top_k: number; min_relevance: number; source: "default" | "document" } | null;
};

export type Candidate = {
  chunk_id: string;
  file_name: string | null;
  page_number: number | null;
  content: string;
  found_by: string[];
  vector: number | null;
  bm25: number | null;
  fused: number | null;
  jev: number | null;
  status: "kept" | "dropped";
  reason: DropReason | null;
  ocr?: boolean;
};

export type ModelCall = {
  kind: "llm" | "jev";
  purpose: string;
  model: string;
  start_ms: number;
  duration_ms: number;
  prompt_tokens: number | null;
  completion_tokens: number | null;
  cost_usd: number | null;
  ok: boolean;
  error: string | null;
};

// Per-document retrieval settings (auto-tune)
export type DocSettings = {
  top_k: number;
  min_relevance: number;
  applied_from_run?: string | null;
  applied_at?: string | null;
};
export type DocSettingsResponse = { settings: DocSettings | null; defaults: { top_k: number; min_relevance: number } };

// Stress test reports (backend/app/services/stress/jobs.py)
export type StressKind = "direct" | "reworded" | "messy" | "unanswerable";
export type StressStatus = "generating" | "running" | "tuning" | "validating" | "done" | "failed";
export type StressItem = {
  id: string;
  kind: StressKind;
  question: string;
  expected_answer: string | null;
  page_number: number | null;
  answer: string | null;
  answer_status: string;
  correct: boolean | null;
  retrieval_hit: boolean | null;
  hallucinated: boolean;
  trace_id: string | null;
};
export type StressSummary = {
  correct: number;
  answerable: number;
  retrieval_hits: number;
  unanswerable: number;
  unanswerable_handled: number;
  hallucinations: number;
  cost_usd: number | null;
  tokens: number;
  by_kind: Partial<Record<StressKind, { correct: number; total: number }>>;
};
export type StressTune = {
  available: boolean;
  best: { min_relevance: number; top_k: number } | null;
  validation: { correct: number; hallucinations: number; retrieval_hits: number; cost_usd: number | null } | null;
  recommend: boolean;
  reason: string | null;
};
export type StressReport = {
  run_id: string;
  document_id: string;
  size: number;
  status: StressStatus;
  progress: { done: number; total: number };
  started_at: string;
  finished_at: string | null;
  settings_used: { top_k: number; min_relevance: number; source: "default" | "document" };
  summary: StressSummary | null;
  items: StressItem[];
  tune: StressTune | null;
  error: string | null;
};
export type StressRunSummary = Pick<
  StressReport,
  "run_id" | "status" | "size" | "started_at" | "finished_at" | "summary" | "settings_used"
>;
