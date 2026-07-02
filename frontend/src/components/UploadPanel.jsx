import { useState } from "react";
import { uploadPdf } from "../api";

export default function UploadPanel({ onUploadSuccess }) {
  const [file, setFile] = useState(null);
  const [status, setStatus] = useState("idle"); // idle | uploading | success | error
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  const handleUpload = async () => {
    if (!file) return;

    setStatus("uploading");
    setError("");

    try {
      const data = await uploadPdf(file);
      setResult(data);
      setStatus("success");
      onUploadSuccess?.(data.filename); // ← notify parent
    } catch (err) {
      setError(err.message);
      setStatus("error");
    }
  };

  return (
    <div className="panel">
      <h2>Upload a Document</h2>
      <input
        type="file"
        accept="application/pdf"
        onChange={(e) => setFile(e.target.files[0])}
      />
      <button onClick={handleUpload} disabled={!file || status === "uploading"}>
        {status === "uploading" ? "Processing..." : "Upload & Ingest"}
      </button>

      {status === "success" && result && (
        <div className="result-box success">
          <p>
            <strong>{result.filename}</strong> ingested successfully
          </p>
          <ul>
            <li>Pages extracted: {result.pages_extracted}</li>
            <li>Chunks created: {result.chunks_created}</li>
            <li>Tables detected: {result.tables_detected}</li>
            <li>Vectors stored: {result.vectors_stored}</li>
          </ul>
        </div>
      )}

      {status === "error" && (
        <div className="result-box error">
          <p>Upload failed: {error}</p>
        </div>
      )}
    </div>
  );
}
