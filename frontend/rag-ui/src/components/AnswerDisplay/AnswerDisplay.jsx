import { useState } from "react";
import { motion as Motion, AnimatePresence } from "framer-motion";
import "./AnswerDisplay.css";

const AnswerDisplay = ({ answer, sources }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(answer);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error("Failed to copy:", err);
    }
  };

  const formatAnswer = (text) => {
    if (!text) return [];
    
    const parts = text.split(/(```[\s\S]*?```|`[^`]+`)/g);
    return parts.map((part, index) => {
      if (part.startsWith("```") && part.endsWith("```")) {
        const code = part.slice(3, -3);
        return { type: "codeblock", content: code, key: index };
      } else if (part.startsWith("`") && part.endsWith("`")) {
        const inline = part.slice(1, -1);
        return { type: "inline", content: inline, key: index };
      } else {
        return { type: "text", content: part, key: index };
      }
    });
  };

  const formattedAnswer = formatAnswer(answer);

  return (
    <Motion.div
      className="answer-display"
      initial={{ opacity: 0, y: 30, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, scale: 0.95 }}
      transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
      layout
    >
      <div className="answer-header">
        <div className="answer-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
            <path d="M12 2L2 7l10 5 10-5-10-5z" />
            <path d="M2 17l10 5 10-5" />
            <path d="M2 12l10 5 10-5" />
          </svg>
        </div>
        <div className="answer-title-group">
          <h3 className="answer-title font-display">AI Response</h3>
          <p className="answer-subtitle">Retrieved from document context</p>
        </div>
        <Motion.button
          className="copy-button"
          onClick={handleCopy}
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          aria-label={copied ? "Copied" : "Copy answer"}
        >
          <AnimatePresence mode="wait">
            {copied ? (
              <Motion.span
                key="copied"
                className="copy-success"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polyline points="20 6 9 17 4 12" />
                </svg>
                Copied!
              </Motion.span>
            ) : (
              <Motion.span
                key="copy"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
                  <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
                </svg>
                Copy
              </Motion.span>
            )}
          </AnimatePresence>
        </Motion.button>
      </div>

      <div className="answer-body">
        <div className="answer-text">
          {formattedAnswer.map((part) => {
            if (part.type === "codeblock") {
              return (
                <div key={part.key} className="code-block-wrapper">
                  <div className="code-block-header">
                    <span className="code-block-label">Code / Technical Detail</span>
                  </div>
                  <pre className="code-block">
                    <code>{part.content}</code>
                  </pre>
                </div>
              );
            } else if (part.type === "inline") {
              return (
                <code key={part.key} className="inline-code">
                  {part.content}
                </code>
              );
            } else {
              return (
                <p key={part.key} className="text-paragraph">
                  {part.content}
                </p>
              );
            }
          })}
        </div>

        {sources && sources.length > 0 && (
          <div className="answer-sources">
            <h4 className="sources-title">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                <polyline points="14 2 14 8 20 8" />
                <line x1="16" y1="13" x2="8" y2="13" />
                <line x1="16" y1="17" x2="8" y2="17" />
              </svg>
              Source Documents
            </h4>
            <div className="sources-list">
              {sources.map((source, idx) => (
                <div key={idx} className="source-item">
                  <span className="source-icon">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                      <polyline points="14 2 14 8 20 8" />
                    </svg>
                  </span>
                  <span className="source-name">{source.name || `Document ${idx + 1}`}</span>
                  {source.page && (
                    <span className="source-page">p. {source.page}</span>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      <div className="answer-glow" aria-hidden="true"></div>
    </Motion.div>
  );
};

export default AnswerDisplay;
