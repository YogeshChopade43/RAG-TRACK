import { useEffect, useRef } from "react";
import { motion as Motion, AnimatePresence } from "framer-motion";
import "./ChatInterface.css";

const ChatInterface = ({ inputValue, onInputChange, onAsk, isLoading, disabled, messages }) => {
  const chatContainerRef = useRef(null);

  const scrollChatToBottom = () => {
    if (chatContainerRef.current) {
      const container = chatContainerRef.current;
      container.scrollTop = container.scrollHeight;
    }
  };

  useEffect(() => {
    scrollChatToBottom();
  }, [messages]);

  const handleKeyPress = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (!isLoading && !disabled && inputValue.trim()) {
        onAsk();
      }
    }
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 20, scale: 0.95 },
    visible: {
      opacity: 1,
      y: 0,
      scale: 1,
      transition: { duration: 0.4, ease: [0.16, 1, 0.3, 1] },
    },
    exit: {
      opacity: 0,
      scale: 0.9,
      transition: { duration: 0.2 },
    },
  };

  const formatMessage = (text) => {
    if (!text) return [];
    
    const parts = text.split(/(`{3}[\s\S]*?`{3}|`[^`]+`)/g);
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

  return (
    <div className="chat-wrapper">
      <div className="chat-header">
        <div className="chat-status">
          <span className="status-indicator"></span>
          <span className="status-text">Ready to query</span>
        </div>
        <h2 className="chat-title font-display">Document Chat</h2>
        <p className="chat-subtitle">Ask anything about your uploaded document</p>
      </div>

      <div className="chat-container" ref={chatContainerRef}>
        {messages.map((msg, index) => (
          <Motion.div
            key={index}
            className={`message ${msg.role === "user" ? "user-message" : "ai-message"}`}
            variants={itemVariants}
            initial="hidden"
            animate="visible"
            layout
          >
            <div className={`message-avatar ${msg.role === "user" ? "user-avatar" : "ai-avatar"}`}>
              {msg.role === "user" ? (
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                  <circle cx="12" cy="7" r="4" />
                </svg>
              ) : (
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <path d="M12 2L2 7l10 5 10-5-10-5z" />
                  <path d="M2 17l10 5 10-5" />
                  <path d="M2 12l10 5 10-5" />
                </svg>
              )}
            </div>
            <div className="message-content">
              <div className={`message-bubble ${msg.role === "user" ? "user-bubble" : "ai-bubble"}`}>
                {msg.role === "user" ? (
                  msg.content
                ) : (
                  <div className="answer-message">
                    {formatMessage(msg.content).map((part) => {
                      if (part.type === "codeblock") {
                        return (
                          <div key={part.key} className="inline-code-block">
                            <code>{part.content}</code>
                          </div>
                        );
                      } else if (part.type === "inline") {
                        return (
                          <code key={part.key} className="inline-code">
                            {part.content}
                          </code>
                        );
                      } else {
                        return <span key={part.key}>{part.content}</span>;
                      }
                    })}
                  </div>
                )}
              </div>
            </div>
          </Motion.div>
        ))}

        <AnimatePresence>
          {isLoading && (
            <Motion.div
              className="message ai-message"
              variants={itemVariants}
              initial="hidden"
              animate="visible"
              exit="exit"
              layout
            >
              <div className="message-avatar ai-avatar">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <path d="M12 2L2 7l10 5 10-5-10-5z" />
                  <path d="M2 17l10 5 10-5" />
                  <path d="M2 12l10 5 10-5" />
                </svg>
              </div>
              <div className="message-content">
                <div className="message-bubble ai-bubble">
                  <div className="typing-indicator">
                    <span className="typing-dot"></span>
                    <span className="typing-dot"></span>
                    <span className="typing-dot"></span>
                  </div>
                </div>
              </div>
            </Motion.div>
          )}
        </AnimatePresence>
      </div>

      <div className="chat-input-wrapper">
        <div className="input-container">
          <textarea
            className="input-premium textarea-premium chat-input"
            placeholder="Ask a question about the document..."
            value={inputValue}
            onChange={(e) => onInputChange(e.target.value)}
            onKeyPress={handleKeyPress}
            disabled={isLoading || disabled}
            rows={1}
            aria-label="Ask a question"
          />
          <Motion.button
            className="send-button"
            onClick={onAsk}
            disabled={isLoading || disabled || !inputValue.trim()}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            aria-label="Send question"
          >
            {isLoading ? (
              <div className="loading-spinner-small"></div>
            ) : (
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="22" y1="2" x2="11" y2="13" />
                <polygon points="22 2 15 22 11 13 2 9 22 2" />
              </svg>
            )}
          </Motion.button>
        </div>
        <p className="input-hint">Press Enter to send • Shift+Enter for new line</p>
      </div>
    </div>
  );
};

export default ChatInterface;
