import { useState } from "react";

function App() {
  const [file, setFile] = useState(null);
  const [documentId, setDocumentId] = useState(null);
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);

  const handleFileChange = async (e) => {
    const selectedFile = e.target.files[0];
    if (!selectedFile) return;

    setFile(selectedFile);
    setError(null);
    setAnswer("");
    setUploading(true);

    try {
      const formData = new FormData();
      formData.append("file", selectedFile);

      const uploadRes = await fetch("http://127.0.0.1:8000/ingest/", {
        method: "POST",
        body: formData
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
  };

  const askQuestion = async () => {
    setError(null);

    if (!question.trim()) {
      setError("Enter a question");
      return;
    }

    setLoading(true);
    setAnswer("");

    try {
      const queryRes = await fetch("http://127.0.0.1:8000/query", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          document_id: documentId,
          question: question
        })
      });

      const queryData = await queryRes.json().catch(async () => {
        return { detail: await queryRes.text() };
      });

      if (!queryRes.ok) {
        setError(queryData.detail || queryData.message || "Query failed");
        return;
      }

      setAnswer(queryData.answer || "");
    } catch (err) {
      setError("Error: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: "20px" }}>
      <h2>RAG Document Upload</h2>

      <input
        type="file"
        onChange={handleFileChange}
        disabled={uploading}
      />

      {uploading && <p style={{ color: "#666" }}>Uploading document...</p>}

      {documentId && (
        <>
          <br /><br />

          <input
            type="text"
            placeholder="Ask something about the document..."
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            style={{ width: "400px", padding: "8px" }}
          />

          <br /><br />

          <button onClick={askQuestion} disabled={loading}>
            {loading ? "Thinking..." : "Ask"}
          </button>
        </>
      )}

      {error && (
        <div style={{ color: "red", margin: "10px 0" }}>
          {error}
        </div>
      )}

      {answer && (
        <>
          <hr />
          <h3>Answer:</h3>
          <div style={{
            border: "1px solid #ddd",
            padding: "14px",
            width: "550px",
            background: "#ffffff",
            borderRadius: "10px",
            color: "#000",
            lineHeight: "1.6",
            whiteSpace: "pre-wrap"
          }}>
            {answer}
          </div>
        </>
      )}
    </div>
  );
}

export default App;
