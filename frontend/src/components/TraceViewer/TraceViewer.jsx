import { useState, useEffect } from "react";
import { motion as Motion, AnimatePresence } from "framer-motion";
import "./TraceViewer.css";

const TraceViewer = ({ traceId }) => {
  const [traceData, setTraceData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [isExpanded, setIsExpanded] = useState(false);
  const [expandedChunks, setExpandedChunks] = useState(new Set());
  const TEXT_PREVIEW_LIMIT = 200;

  useEffect(() => {
    if (!traceId) return;

    const fetchTrace = async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await fetch(`http://127.0.0.1:8000/query/trace/${traceId}`);
        if (!res.ok) throw new Error("Failed to fetch trace data");
        const data = await res.json();
        setTraceData(data);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchTrace();
  }, [traceId]);

  const getScoreColor = (score) => {
    if (score >= 0.8) return "score-high";
    if (score >= 0.5) return "score-medium";
    return "score-low";
  };

  const toggleChunkExpansion = (chunkId, index) => {
    const key = String(chunkId || index);
    setExpandedChunks((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  const formatLatency = (ms) => {
    if (ms < 1000) return `${ms.toFixed(0)}ms`;
    return `${(ms / 1000).toFixed(2)}s`;
  };

  const containerVariants = {
    hidden: { opacity: 0, height: 0 },
    visible: {
      opacity: 1,
      height: "auto",
      transition: { duration: 0.4, ease: [0.16, 1, 0.3, 1] },
    },
    exit: {
      opacity: 0,
      height: 0,
      transition: { duration: 0.3 },
    },
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 10 },
    visible: (i) => ({
      opacity: 1,
      y: 0,
      transition: { delay: i * 0.05, duration: 0.3 },
    }),
  };

  if (!traceId) return null;

  return (
    <div className="trace-viewer">
      <button
        className="trace-toggle"
        onClick={() => setIsExpanded(!isExpanded)}
        aria-expanded={isExpanded}
      >
        <svg
          className={`trace-chevron ${isExpanded ? "expanded" : ""}`}
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
        >
          <polyline points="6 9 12 15 18 9" />
        </svg>
        <span>View Trace Details</span>
        {loading && <div className="trace-loading-dot" />}
      </button>

      <AnimatePresence>
        {isExpanded && (
          <Motion.div
            className="trace-content"
            variants={containerVariants}
            initial="hidden"
            animate="visible"
            exit="exit"
          >
            {error && (
              <div className="trace-error">
                <span>Error loading trace: {error}</span>
              </div>
            )}

            {traceData && (
              <>
                <Motion.div className="trace-section" variants={containerVariants}>
                  <h4 className="trace-section-title">Pipeline Overview</h4>
                  <div className="trace-overview">
                    <div className="trace-id-badge">
                      <span className="trace-id-label">Trace ID</span>
                      <code className="trace-id-value">{traceData.trace_id?.slice(0, 8)}...</code>
                    </div>
                    <div className="latency-timeline">
                      {Object.entries(traceData.latency || {}).map(([stage, ms], i) => (
                        <Motion.div
                          key={stage}
                          className="latency-bar"
                          variants={itemVariants}
                          custom={i}
                        >
                          <div className="latency-label">{stage}</div>
                          <div className="latency-track">
                            <Motion.div
                              className="latency-fill"
                              style={{ width: `${Math.min(ms / 10, 100)}%` }}
                            />
                          </div>
                          <span className="latency-value">{formatLatency(ms)}</span>
                        </Motion.div>
                      ))}
                    </div>
                  </div>
                </Motion.div>

                <Motion.div className="trace-section" variants={containerVariants}>
                  <h4 className="trace-section-title">Query Processing</h4>
                  <div className="query-info">
                    <div className="query-item">
                      <span className="query-label">Original</span>
                      <code className="query-value">{traceData.original_query}</code>
                    </div>
                    {traceData.rewritten_query && (
                      <div className="query-item">
                        <span className="query-label">Rewritten</span>
                        <code className="query-value">{traceData.rewritten_query}</code>
                      </div>
                    )}
                    {traceData.decomposed_queries?.length > 0 && (
                      <div className="query-item">
                        <span className="query-label">
                          Sub-queries ({traceData.decomposed_queries.length})
                        </span>
                        <ul className="sub-queries-list">
                          {traceData.decomposed_queries.map((q, i) => (
                            <Motion.li key={i} variants={itemVariants} custom={i}>
                              <code>{q}</code>
                            </Motion.li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                </Motion.div>

                <Motion.div className="trace-section" variants={containerVariants}>
                  <h4 className="trace-section-title">
                    Retrieved Chunks ({traceData.retrieved_chunks?.length || 0})
                  </h4>
                  <div className="chunks-list">
                    {traceData.retrieved_chunks?.map((chunk, i) => (
                      <Motion.div
                        key={chunk.chunk_id || i}
                        className="chunk-card"
                        variants={itemVariants}
                        custom={i}
                      >
                        <div className="chunk-header">
                          <span className={`score-badge ${getScoreColor(chunk.score)}`}>
                            {chunk.score?.toFixed(3)}
                          </span>
                          <span className="chunk-meta">
                            {chunk.metadata?.file_name && (
                              <span className="meta-item">{chunk.metadata.file_name}</span>
                            )}
                            {chunk.metadata?.page_number && (
                              <>
                                <span className="meta-separator">|</span>
                                <span className="meta-item">p{chunk.metadata.page_number}</span>
                              </>
                            )}
                          </span>
                        </div>
                        <div className="chunk-content">
                          {chunk.content != null && chunk.content.length > TEXT_PREVIEW_LIMIT && !expandedChunks.has(String(chunk.chunk_id || i))
                            ? `${chunk.content.slice(0, TEXT_PREVIEW_LIMIT)}…`
                            : chunk.content}
                        </div>
                        {chunk.content != null && chunk.content.length > TEXT_PREVIEW_LIMIT && (
                          <button
                            className="chunk-expand-btn"
                            onClick={() => toggleChunkExpansion(chunk.chunk_id, i)}
                          >
                            <span>{expandedChunks.has(String(chunk.chunk_id || i)) ? "Show less" : "Show more"}</span>
                            <svg
                              className={`chunk-expand-icon ${expandedChunks.has(String(chunk.chunk_id || i)) ? "expanded" : ""}`}
                              viewBox="0 0 24 24"
                              fill="none"
                              stroke="currentColor"
                              strokeWidth="2"
                            >
                              <polyline points="6 9 12 15 18 9" />
                            </svg>
                          </button>
                        )}
                        {(chunk.semantic_score !== undefined || chunk.keyword_score !== undefined) && (
                          <div className="ranking-signals">
                            {chunk.semantic_score !== undefined && (
                              <span className="signal">sem: {chunk.semantic_score?.toFixed(3)}</span>
                            )}
                            {chunk.keyword_score !== undefined && (
                              <span className="signal">kw: {chunk.keyword_score?.toFixed(3)}</span>
                            )}
                          </div>
                        )}
                      </Motion.div>
                    ))}
                  </div>
                </Motion.div>

                {traceData.bm25_results?.length > 0 && (
                  <Motion.div className="trace-section" variants={containerVariants}>
                    <h4 className="trace-section-title">Hybrid Search Details</h4>
                    <div className="hybrid-details">
                      <div className="hybrid-stats">
                        <div className="stat">
                          <span className="stat-value">{traceData.bm25_results?.length}</span>
                          <span className="stat-label">BM25 Results</span>
                        </div>
                        <div className="stat">
                          <span className="stat-value">{traceData.retrieved_chunks?.length}</span>
                          <span className="stat-label">Vector Results</span>
                        </div>
                      </div>
                      {traceData.fusion_details && (
                        <div className="fusion-info">
                          <span className="fusion-label">Fusion Weights</span>
                          <code className="fusion-value">
                            {JSON.stringify(traceData.fusion_details)}
                          </code>
                        </div>
                      )}
                    </div>
                  </Motion.div>
                )}

                {traceData.reranked_chunks?.length > 0 && (
                  <Motion.div className="trace-section" variants={containerVariants}>
                    <h4 className="trace-section-title">Reranked Chunks</h4>
                    <div className="chunks-list">
                      {traceData.reranked_chunks.map((chunk, i) => (
                        <Motion.div
                          key={chunk.chunk_id || i}
                          className="chunk-card reranked"
                          variants={itemVariants}
                          custom={i}
                        >
                          <div className="chunk-header">
                            <span className={`score-badge ${getScoreColor(chunk.final_score)}`}>
                              {chunk.final_score?.toFixed(3)}
                            </span>
                            <span className="rank-badge">#{chunk.rank}</span>
                          </div>
                          <div className="ranking-signals-full">
                            {chunk.semantic_score !== undefined && (
                              <span className="signal-bar">
                                <span className="signal-name">sem</span>
                                <span className="signal-value">{chunk.semantic_score?.toFixed(3)}</span>
                              </span>
                            )}
                            {chunk.keyword_score !== undefined && (
                              <span className="signal-bar">
                                <span className="signal-name">kw</span>
                                <span className="signal-value">{chunk.keyword_score?.toFixed(3)}</span>
                              </span>
                            )}
                            {chunk.llm_relevance_score !== undefined && (
                              <span className="signal-bar">
                                <span className="signal-name">llm</span>
                                <span className="signal-value">{chunk.llm_relevance_score?.toFixed(3)}</span>
                              </span>
                            )}
                          </div>
                        </Motion.div>
                      ))}
                    </div>
                  </Motion.div>
                )}
              </>
            )}
          </Motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default TraceViewer;