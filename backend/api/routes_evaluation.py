# api/routes_evaluation.py
import os, json
from fastapi import APIRouter, HTTPException

router = APIRouter()

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "..", "evaluation", "results")


@router.get("/evaluation/latest")
def get_latest_scores():
    """Returns the most recent RAGAS aggregate scores + metadata."""
    if not os.path.isdir(RESULTS_DIR):
        raise HTTPException(status_code=404, detail="No evaluation results found.")

    score_files = [f for f in os.listdir(RESULTS_DIR) if f.startswith("scores_")]
    if not score_files:
        raise HTTPException(status_code=404, detail="No evaluation results found.")

    latest_file = sorted(score_files)[-1]  # filenames are timestamped, sort = chronological
    with open(os.path.join(RESULTS_DIR, latest_file), "r", encoding="utf-8") as f:
        scores = json.load(f)

    # Also pull raw_results count for "N questions evaluated" context
    raw_filename = latest_file.replace("scores_", "raw_results_")
    raw_path = os.path.join(RESULTS_DIR, raw_filename)
    question_count = None
    if os.path.exists(raw_path):
        with open(raw_path, "r", encoding="utf-8") as f:
            raw = json.load(f)
            question_count = len(raw)

    return {
        "scores": scores,
        "question_count": question_count,
        "timestamp": latest_file.replace("scores_", "").replace(".json", ""),
    }