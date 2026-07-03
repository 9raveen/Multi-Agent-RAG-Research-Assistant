import AgentTracePanel from "./AgentTracePanel";

export default function AnswerCard({ result }) {
  if (!result) return null;

  const { answer, critique_passed, revisions_taken, sources, trace } = result;

  return (
    <div className="answer-card">
      <div className={`badge ${critique_passed ? "verified" : "unverified"}`}>
        {critique_passed ? "Verified" : "Best effort — unverified"}
      </div>

      <p className="answer-text">{answer}</p>

      <p className="meta">Revisions taken: {revisions_taken}</p>

      {sources && sources.length > 0 && (
        <div className="sources">
          <h4>Sources</h4>
          <ul>
            {sources.map((s, i) => (
              <li key={i}>
                {s.source_file} — page {s.page_number}
                {s.chunk_type === "table" && (
                  <span className="tag"> [table]</span>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}

      <AgentTracePanel trace={trace} />
    </div>
  );
}
