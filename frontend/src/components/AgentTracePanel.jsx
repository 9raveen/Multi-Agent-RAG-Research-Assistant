// components/AgentTracePanel.jsx
const NODE_LABELS = {
  research_node: "Research",
  synthesis_node: "Synthesis",
  critique_node: "Critique",
};

export default function AgentTracePanel({ trace }) {
  if (!trace || trace.length === 0) return null;

  return (
    <div className="trace-panel">
      <h4>Agent Pipeline</h4>
      <div className="trace-steps">
        {trace.map((step, i) => (
          <div
            key={i}
            className={`trace-step ${step.rate_limited ? "trace-step--error" : "trace-step--ok"}`}
          >
            <span className="trace-step__node">
              {NODE_LABELS[step.node] || step.node}
            </span>

            {step.node === "research_node" && (
              <span className="trace-step__detail">
                {step.chunks_retrieved} chunks retrieved
              </span>
            )}

            {step.node === "synthesis_node" && step.rate_limited && (
              <span className="trace-step__detail trace-step__detail--error">
                rate limited
              </span>
            )}

            {step.node === "critique_node" && (
              <span className="trace-step__detail">
                {step.critique_passed
                  ? "passed"
                  : step.critique_feedback
                    ? "failed" // critique actually ran and produced a verdict
                    : "skipped"}{" "}
                // only true skip: no feedback exists at all
              </span>
            )}

            {step.critique_feedback && (
              <p className="trace-step__feedback">{step.critique_feedback}</p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
