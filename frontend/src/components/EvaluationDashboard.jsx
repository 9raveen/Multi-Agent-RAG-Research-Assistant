// components/EvaluationDashboard.jsx
import { useEffect, useState } from "react";

const METRIC_LABELS = {
  faithfulness: "Faithfulness",
  answer_relevancy: "Answer Relevancy",
  context_precision: "Context Precision",
  context_recall: "Context Recall",
};

export default function EvaluationDashboard() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetch("http://localhost:8000/evaluation/latest") // swap to env var before deploy
      .then((res) => {
        if (!res.ok) throw new Error("No evaluation results available yet.");
        return res.json();
      })
      .then(setData)
      .catch((err) => setError(err.message));
  }, []);

  if (error)
    return <div className="eval-dashboard eval-dashboard--empty">{error}</div>;
  if (!data) return null;

  return (
    <div className="eval-dashboard">
      <h4>RAGAS Evaluation</h4>
      <p className="eval-dashboard__meta">
        {data.question_count} questions evaluated
      </p>
      <div className="eval-metrics">
        {Object.entries(data.scores).map(([key, value]) => (
          <div key={key} className="eval-metric">
            <span className="eval-metric__label">
              {METRIC_LABELS[key] || key}
            </span>
            <div className="eval-metric__bar-track">
              <div
                className="eval-metric__bar-fill"
                style={{ width: `${value * 100}%` }}
              />
            </div>
            <span className="eval-metric__value">
              {(value * 100).toFixed(1)}%
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
