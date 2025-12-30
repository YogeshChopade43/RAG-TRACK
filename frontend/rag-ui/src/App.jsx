import { useState } from "react";

function App() {
  const [file, setFile] = useState(null);
  const [response, setResponse] = useState(null);

  const upload = async () => {
  console.log("Upload button clicked");

  if (!file) {
    alert("No file selected");
    return;
  }

  console.log("File selected:", file.name);

  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch("http://127.0.0.1:8000/ingest/", {
    method: "POST",
    body: formData
  });

  const data = await res.json();
  console.log("Server response:", data);
  setResponse(data);
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
    </div>
  );
}

export default App;
