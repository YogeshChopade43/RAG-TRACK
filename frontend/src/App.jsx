import { useState, useEffect, useCallback, useRef } from "react";
import { motion as Motion, AnimatePresence, useScroll, useTransform } from "framer-motion";
import { useAuth } from "./contexts/AuthContext.jsx";
import HeroSection from "./components/HeroSection/HeroSection";
import PremiumFileUpload from "./components/PremiumFileUpload/PremiumFileUpload";
import ChatInterface from "./components/ChatInterface/ChatInterface";
import "./App.css";

function App() {
  const { getAuthHeaders, logout } = useAuth();
  const API_BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
  const [file, setFile] = useState(null);
  const [documentId, setDocumentId] = useState(null);
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);
  const [llmApiKey, setLlmApiKey] = useState(() => sessionStorage.getItem("llm_api_key") || "");
  const [apiKeyTest, setApiKeyTest] = useState({ testing: false, valid: false, message: "" });
  const apiKeyReady = !!llmApiKey && apiKeyTest.valid;

  const uploadSectionRef = useRef(null);
  const { scrollY } = useScroll();
  const heroOpacity = useTransform(scrollY, [0, 400], [1, 0]);
  const heroScale = useTransform(scrollY, [0, 400], [1, 0.9]);

  const scrollToUpload = useCallback(() => {
    uploadSectionRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, []);

  const testLlmApiKey = useCallback(async () => {
    setApiKeyTest({ testing: true, valid: false, message: "" });
    try {
      const res = await fetch(`${API_BASE}/auth/test-api-key`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...getAuthHeaders() },
        body: JSON.stringify({ api_key: llmApiKey }),
      });
      const data = await res.json();
      setApiKeyTest({ testing: false, valid: data.valid, message: data.message });
    } catch (err) {
      setApiKeyTest({ testing: false, valid: false, message: "Test failed: " + err.message });
    }
  }, [llmApiKey, API_BASE, getAuthHeaders]);

  const handleFileSelect = useCallback(async (selectedFile) => {
    if (!selectedFile) return;

    setFile(selectedFile);
    setError(null);
    setMessages([]);
    setDocumentId(null);
    setUploading(true);

    try {
      const formData = new FormData();
      formData.append("file", selectedFile);

      const uploadRes = await fetch(`${API_BASE}/ingest/`, {
        method: "POST",
        body: formData,
        headers: {
          ...getAuthHeaders(),
          ...(llmApiKey ? { "X-User-OpenRouter-Key": llmApiKey } : {}),
        },
      });

      const uploadData = await uploadRes.json();

      if (!uploadRes.ok) {
        setError(uploadData.detail || "Upload failed");
        setDocumentId(null);
        setUploading(false);
        return;
      }

      setDocumentId(uploadData.document_id);
      setError(null);
    } catch (err) {
      setError("Upload error: " + err.message);
      setDocumentId(null);
    } finally {
      setUploading(false);
    }
  }, [getAuthHeaders]);

  const askQuestion = useCallback(async () => {
    setError(null);

    if (!question.trim()) {
      setError("Enter a question");
      return;
    }

    if (!documentId) {
      setError("Please upload a document first");
      return;
    }

    const userQuestion = question;
    setQuestion("");
    setLoading(true);

    // Add user question to messages
    setMessages((prev) => [...prev, { role: "user", content: userQuestion }]);

    try {
      const queryRes = await fetch(`${API_BASE}/query`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...getAuthHeaders(),
          ...(llmApiKey ? { "X-User-OpenRouter-Key": llmApiKey } : {}),
        },
        body: JSON.stringify({
          document_id: documentId,
          question: userQuestion,
        }),
      });

      const queryData = await queryRes.json().catch(async () => {
        return { detail: await queryRes.text() };
      });

      if (!queryRes.ok) {
        setError(queryData.detail || queryData.message || "Query failed");
        // Remove the user message if query failed
        setMessages((prev) => prev.slice(0, -1));
        return;
      }

const answer = queryData.answer || "";
       setMessages((prev) => [...prev, { role: "assistant", content: answer, traceId: queryData.trace_id }]);
    } catch (err) {
      setError("Error: " + err.message);
      setMessages((prev) => prev.slice(0, -1));
    } finally {
      setLoading(false);
    }
  }, [question, documentId, getAuthHeaders]);

  const handleReset = useCallback(() => {
    setFile(null);
    setDocumentId(null);
    setQuestion("");
    setMessages([]);
    setError(null);
  }, []);

  useEffect(() => {
    if (llmApiKey) {
      sessionStorage.setItem("llm_api_key", llmApiKey);
    } else {
      sessionStorage.removeItem("llm_api_key");
    }
  }, [llmApiKey]);

  useEffect(() => {
    const handleStorage = () => {
      const key = sessionStorage.getItem("llm_api_key") || "";
      setLlmApiKey(key);
    };
    window.addEventListener("storage", handleStorage);
    return () => window.removeEventListener("storage", handleStorage);
  }, []);

  // Page title update
  useEffect(() => {
    const lastMessage = messages[messages.length - 1];
    document.title = lastMessage?.role === "assistant"
      ? "RAG-TRACK | Document Intelligence"
      : documentId
      ? "Querying Document"
      : "RAG-TRACK | Upload Document";
  }, [messages, documentId]);

  return (
    <div className="app">
      {/* Animated Gradient Background */}
      <div className="mesh-gradient"></div>

      {/* Header */}
      <header className="app-header">
        <div className="llm-status-indicator">
          <span className={`llm-status-dot ${apiKeyReady ? "ready" : "missing"}`}></span>
          <span className="llm-status-text">
            {apiKeyReady ? "LLM Ready" : "LLM Not Configured"}
          </span>
        </div>
        <button className="logout-button" onClick={logout}>
          Sign Out
        </button>
      </header>

      {/* API Key Setup Card */}
      {!apiKeyReady && (
        <div className="main-content container" id="llm-config">
          <Motion.div
            className="card llm-config-card"
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
          >
            <div className="llm-config-header">
              <div>
                <h2 className="llm-config-title">Configure LLM Provider</h2>
                <p className="llm-config-subtitle">
                  Enter your OpenRouter API key to enable the RAG chatbot. Your key is stored only in this browser session and is forgotten when you log out.
                </p>
              </div>
            </div>
            <div className="llm-config-form">
              <input
                type="password"
                value={llmApiKey}
                onChange={(e) => {
                  setLlmApiKey(e.target.value);
                  if (apiKeyTest.valid) {
                    setApiKeyTest({ testing: false, valid: false, message: "" });
                  }
                }}
                placeholder="sk-or-..."
                className="llm-input-large"
                disabled={apiKeyTest.testing}
              />
              <button
                onClick={testLlmApiKey}
                disabled={apiKeyTest.testing || !llmApiKey}
                className="btn btn-primary llm-test-btn-large"
              >
                {apiKeyTest.testing ? "Testing..." : "Test & Continue"}
              </button>
              {apiKeyTest.message && !apiKeyTest.valid && (
                <span className={`llm-test-status ${apiKeyTest.valid ? "valid" : "invalid"}`}>
                  {apiKeyTest.message}
                </span>
              )}
            </div>
            {apiKeyTest.valid && (
              <div className="llm-config-success">
                ✓ API key verified. You can now use the chatbot.
              </div>
            )}
          </Motion.div>
        </div>
      )}

      {/* Hero Section */}
      <Motion.section style={{ opacity: heroOpacity, scale: heroScale }}>
        <HeroSection onUploadClick={scrollToUpload} disabled={!apiKeyReady} />
      </Motion.section>

      {/* Main Content */}
      <main className="main-content container" id="main-content">
        <AnimatePresence mode="wait">
          {!documentId ? (
            <Motion.div
              key="upload"
              className="upload-section"
              ref={uploadSectionRef}
              initial={{ opacity: 0, y: 50 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -50 }}
              transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
            >
              <PremiumFileUpload
                onFileSelect={handleFileSelect}
                isUploading={uploading}
                error={error}
                disabled={!apiKeyReady}
              />

              {file && !uploading && (
                <Motion.div
                  className="file-confirmation glass"
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ delay: 0.2 }}
                >
                  <div className="file-icon">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                      <polyline points="14 2 14 8 20 8" />
                    </svg>
                  </div>
                  <div className="file-info">
                    <span className="file-name">{file.name}</span>
                    <span className="file-size">{(file.size / 1024 / 1024).toFixed(2)} MB</span>
                  </div>
                  <button className="reset-button" onClick={handleReset} aria-label="Remove file">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <line x1="18" y1="6" x2="6" y2="18" />
                      <line x1="6" y1="6" x2="18" y2="18" />
                    </svg>
                  </button>
                </Motion.div>
              )}
            </Motion.div>
          ) : (
            <Motion.div
              key="chat"
              className="chat-section"
              initial={{ opacity: 0, y: 50 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -50 }}
              transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
            >
              {file && (
                <Motion.div
                  className="active-document glass"
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.1 }}
                >
                  <span className="document-label">Active Document</span>
                  <div className="document-info">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                      <polyline points="14 2 14 8 20 8" />
                    </svg>
                    <span className="document-name">{file.name}</span>
                    <button className="change-doc-btn" onClick={handleReset}>
                      Change
                    </button>
                  </div>
                </Motion.div>
              )}

              <div className="chat-wrapper-outer">
              <ChatInterface
                inputValue={question}
                onInputChange={setQuestion}
                onAsk={askQuestion}
                isLoading={loading}
                disabled={!documentId || !apiKeyReady}
                messages={messages}
              />
              </div>

              <AnimatePresence>
                {error && (
                  <Motion.div
                    className="error-message"
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -10 }}
                    role="alert"
                  >
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <circle cx="12" cy="12" r="10" />
                      <line x1="12" y1="8" x2="12" y2="12" />
                      <line x1="12" y1="16" x2="12.01" y2="16" />
                    </svg>
                    {error}
                    <button className="error-dismiss" onClick={() => setError(null)} aria-label="Dismiss error">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <line x1="18" y1="6" x2="6" y2="18" />
                        <line x1="6" y1="6" x2="18" y2="18" />
                      </svg>
                    </button>
                  </Motion.div>
                )}
              </AnimatePresence>
            </Motion.div>
          )}
        </AnimatePresence>
      </main>

      {/* Footer */}
      <footer className="premium-footer">
        <div className="container">
          <div className="footer-content">
            <p className="footer-brand">
              <span className="brand-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M12 2L2 7l10 5 10-5-10-5z" />
                  <path d="M2 17l10 5 10-5" />
                  <path d="M2 12l10 5 10-5" />
                </svg>
              </span>
              RAG-TRACK
            </p>
            <p className="footer-tagline">Advanced RAG with Query Decomposition & Observability</p>
            <div className="footer-glow" aria-hidden="true"></div>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;