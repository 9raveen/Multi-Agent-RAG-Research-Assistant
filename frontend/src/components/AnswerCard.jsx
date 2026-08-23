import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import AgentTracePanel from "./AgentTracePanel";

function getVerificationStatus(trace, critiquePassed) {
  const critiqueStep = [...(trace || [])]
    .reverse()
    .find((step) => step.node === "critique_node");

  // No critique step available
  if (!critiqueStep) {
    return {
      label: critiquePassed ? "Accepted" : "Best effort — unverified",
      className: critiquePassed ? "accepted" : "unverified",
    };
  }

  const feedback = critiqueStep.critique_feedback || "";

  // Critique infrastructure failed, so the answer was accepted
  // without an actual verification verdict.
  const acceptedWithoutVerification =
    feedback.includes("critique service was unavailable") ||
    feedback.includes("critique output could not be processed") ||
    feedback.includes("critique context was too large") ||
    feedback.includes("critique did not complete");

  if (acceptedWithoutVerification) {
    return {
      label: "Accepted — not verified",
      className: "unverified",
    };
  }

  // Summary intentionally skips critique.
  if (
    feedback === "Summary generated through map-reduce summarization process"
  ) {
    return {
      label: "Summary generated",
      className: "accepted",
    };
  }

  // Actual successful critique
  if (critiquePassed) {
    return {
      label: "Verified",
      className: "verified",
    };
  }

  // Actual critique failure
  return {
    label: "Best effort — unverified",
    className: "unverified",
  };
}

export default function AnswerCard({ result }) {
  if (!result) return null;

  const { answer, critique_passed, revisions_taken, sources, trace } = result;

  const verificationStatus = getVerificationStatus(trace, critique_passed);

  return (
    <div className="answer-card">
      {/* Verification badge */}
      <div className={`badge ${verificationStatus.className}`}>
        {verificationStatus.label}
      </div>

      {/* Render Markdown answer */}
      <div className="answer-text">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>
          {answer || ""}
        </ReactMarkdown>
      </div>

      {/* Revision metadata */}
      <p className="meta">Revisions taken: {revisions_taken ?? 0}</p>

      {/* Sources */}
      {sources && sources.length > 0 && (
        <div className="sources">
          <h4>Sources</h4>

          <ul>
            {sources.map((source, index) => (
              <li key={index}>
                {source.source_file}
                {" — page "}
                {source.page_number}

                {source.chunk_type === "table" && (
                  <span className="tag"> [table]</span>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Agent execution trace */}
      <AgentTracePanel trace={trace} />
    </div>
  );
}
