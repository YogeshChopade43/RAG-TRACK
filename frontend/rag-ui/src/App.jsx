import { useState } from "react";

function App() {
  const [file, setFile] = useState(null);
  const [response, setResponse] = useState(null);
  const [documentId, setDocumentId] = useState(null);
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const upload = async () => {
    setError(null);

    if (!file) {
      setError("No file selected");
      return;
    }

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch("http://127.0.0.1:8000/ingest/", {
        method: "POST",
        body: formData
      });

      const data = await res.json();

      if (!res.ok) {
        setError(data.detail || "Upload failed");
        return;
      }

      setResponse(data);
      setDocumentId(data.document_id);
    } catch (err) {
      setError("Upload failed: " + err.message);
    }
  };

  const askQuestion = async () => {
    setError(null);

    if (!documentId) {
      setError("Upload a document first!");
      return;
    }

    if (!question.trim()) {
      setError("Enter a question");
      return;
    }

    setLoading(true);
    setAnswer("");

    try {
      const response = await fetch("http://127.0.0.1:8000/query", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          document_id: documentId,
          question: question
        })
      });

      const data = await response.json().catch(async () => {
        return { detail: await response.text() };
      });

      if (!response.ok) {
        setError(data.detail || data.message || "Query failed");
        return;
      }

      setAnswer(data.answer || "");
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
        onChange={(e) => setFile(e.target.files[0])}
      />

      <br /><br />

      <button onClick={upload}>Upload</button>

      {response && (
        <>
          <h4>Server Response</h4>
          <pre>{JSON.stringify(response, null, 2)}</pre>
        </>
      )}

      {error && (
        <div style={{ color: "red", margin: "10px 0" }}>
          {error}
        </div>
      )}

      <hr />

      <h3>Ask a Question</h3>

      <input
        type="text"
        placeholder="Ask something about the uploaded document..."
        value={question}
        onChange={(e) => setQuestion(e.target.value)}
        style={{ width: "400px", padding: "8px" }}
      />

      <br /><br />

      <button onClick={askQuestion} disabled={loading}>
        Ask
      </button>

      {loading && <p>Thinking...</p>}

      {answer && (
        <>
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
