import { useState } from "react";
import { askQuery } from "../api";
import AnswerCard from "./AnswerCard";

export default function QueryPanel({ documentScope }) {
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("idle"); // idle | loading | success | error
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  const handleAsk = async () => {
    if (!query.trim()) return;

    setStatus("loading");
    setError("");
    setResult(null);

    try {
      const data = await askQuery(query, documentScope);
      setResult(data);
      setStatus("success");
    } catch (err) {
      setError(err.message);
      setStatus("error");
    }
  };

  return (
    <div className="panel">
      <h2>Ask a Question</h2>
      {documentScope && (
        <p className="scope-hint">Searching within: {documentScope}</p>
      )}
      <textarea
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Ask something about your uploaded documents..."
        rows={3}
      />
      <button
        onClick={handleAsk}
        disabled={!query.trim() || status === "loading"}
      >
        {status === "loading" ? "Thinking..." : "Ask"}
      </button>

      {status === "loading" && (
        <p className="loading-hint">
          Running research → synthesis → critique pipeline (may retry if the
          first answer isn't well-supported)...
        </p>
      )}

      {status === "error" && (
        <div className="result-box error">
          <p>Query failed: {error}</p>
        </div>
      )}

      <AnswerCard result={result} />
    </div>
  );
}
