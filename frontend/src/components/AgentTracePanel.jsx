// components/AgentTracePanel.jsx

const NODE_LABELS = {
  research_node: "Research",
  synthesis_node: "Synthesis",
  critique_node: "Critique",
};

function getCritiqueStatus(step) {
  const feedback = step.critique_feedback || "";

  if (
    feedback === "Summary generated through map-reduce summarization process"
  ) {
    return {
      label: "skipped",
      className: "trace-step__detail--skipped",
    };
  }

  if (
    feedback.includes("critique service was unavailable") ||
    feedback.includes("critique output could not be processed") ||
    feedback.includes("critique context was too large") ||
    feedback.includes("critique did not complete")
  ) {
    return {
      label: "accepted without verification",
      className: "trace-step__detail--warning",
    };
  }

  if (step.critique_passed) {
    return {
      label: "passed",
      className: "trace-step__detail--success",
    };
  }

  if (feedback) {
    return {
      label: "failed",
      className: "trace-step__detail--error",
    };
  }

  return {
    label: "skipped",
    className: "trace-step__detail--skipped",
  };
}

export default function AgentTracePanel({ trace }) {
  if (!trace || trace.length === 0) {
    return null;
  }

  return (
    <div className="trace-panel">
      <h4>Agent Pipeline</h4>

      <div className="trace-steps">
        {trace.map((step, index) => {
          const critiqueStatus =
            step.node === "critique_node" ? getCritiqueStatus(step) : null;

          const hasError =
            step.rate_limited ||
            (step.node === "critique_node" &&
              critiqueStatus?.label === "failed");

          return (
            <div
              key={`${step.node}-${index}`}
              className={`trace-step ${
                hasError ? "trace-step--error" : "trace-step--ok"
              }`}
            >
              {/* Node name */}
              <span className="trace-step__node">
                {NODE_LABELS[step.node] || step.node}
              </span>

              {/* Research details */}
              {step.node === "research_node" && (
                <span className="trace-step__detail">
                  {step.chunks_retrieved ?? 0} chunks retrieved
                </span>
              )}

              {/* Synthesis details */}
              {step.node === "synthesis_node" && step.rate_limited && (
                <span
                  className="
                      trace-step__detail
                      trace-step__detail--error
                    "
                >
                  Rate limited
                </span>
              )}

              {/* Critique details */}
              {step.node === "critique_node" && critiqueStatus && (
                <span
                  className={`
                      trace-step__detail
                      ${critiqueStatus.className}
                    `}
                >
                  {critiqueStatus.label}
                </span>
              )}

              {/* Critique feedback */}
              {step.node === "critique_node" &&
                step.critique_feedback &&
                step.critique_feedback !== "looks good" && (
                  <p className="trace-step__feedback">
                    {step.critique_feedback}
                  </p>
                )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
