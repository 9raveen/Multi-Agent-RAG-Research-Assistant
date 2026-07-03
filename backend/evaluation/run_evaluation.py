# run_evaluation.py
# Runs the benchmark dataset through the actual LangGraph pipeline,
# collects (question, answer, retrieved_contexts, ground_truth) for each,
# then scores the results using RAGAS metrics.
import sys, os, json
from datetime import datetime

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

# ── Workaround for a known ragas bug (github.com/explodinggradients/ragas/issues/2741) ──
# ragas 0.4.3 unconditionally imports ChatVertexAI from a langchain_community
# submodule that was removed upstream in langchain_community 0.4.x (Google's
# integrations were split into a separate langchain-google-vertexai package).
# This is an unresolved packaging bug in ragas itself, not a local issue.
# We never use Vertex AI in this project, so we inject a harmless stub module
# to satisfy the import and let ragas load normally.
import types

_stub = types.ModuleType("langchain_community.chat_models.vertexai")
class ChatVertexAI:  # placeholder — never instantiated, never used
    pass
_stub.ChatVertexAI = ChatVertexAI
sys.modules["langchain_community.chat_models.vertexai"] = _stub
# ── End workaround ──

from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

from ragas import evaluate, EvaluationDataset, RunConfig
from openai import OpenAI as OpenAICompatibleClient
from ragas.llms import llm_factory
from langchain_huggingface import HuggingFaceEmbeddings as LangchainHFEmbeddings
from ragas.embeddings import LangchainEmbeddingsWrapper
from ragas.metrics import (
    Faithfulness,
    AnswerRelevancy,
    ContextPrecision,
    ContextRecall,
)

from agents.graph import build_graph
from evaluation.benchmark_dataset import BENCHMARK

load_dotenv()

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")
os.makedirs(RESULTS_DIR, exist_ok=True)


def run_pipeline_on_benchmark(document_scope: str | None = None) -> list[dict]:
    """
    Runs every benchmark question through the actual LangGraph pipeline
    (same graph.py used in production) and collects everything RAGAS needs:
    question, generated answer, retrieved contexts, and ground truth.
    """
    graph = build_graph()
    collected = []

    for i, item in enumerate(BENCHMARK, start=1):
        print(f"[{i}/{len(BENCHMARK)}] Running: {item['question']}")

        initial_state = {
            "query": item["question"],
            "document_scope": document_scope,
            "retrieved_chunks": [],
            "synthesis_output": "",
            "critique_passed": False,
            "critique_feedback": "",
            "revision_count": 0,
            "rate_limited": False,
            "previous_answer": "",
        }

        result = graph.invoke(initial_state)
        contexts = [chunk["text"] for chunk in result["retrieved_chunks"]]

        collected.append({
            "question": item["question"],
            "answer": result["synthesis_output"],
            "contexts": contexts,
            "ground_truth": item["ground_truth"],
            "_critique_passed": result["critique_passed"],
            "_revisions_taken": result["revision_count"],
            "_rate_limited": result.get("rate_limited", False),  # NEW — carry the flag through
        })

    return collected


def score_with_ragas(collected: list[dict]):
    """
    Scores the collected results using RAGAS metrics, with Groq as the
    judge LLM (avoids OpenAI/Google API access, same reasoning as the rest
    of this project) and the local sentence-transformers model for embeddings.

    NOTE: We use the openai SDK pointed at Groq's OpenAI-compatible endpoint
    (https://api.groq.com/openai/v1) rather than the native `groq` SDK.
    This is a workaround for a bug in ragas 0.4.3's provider dispatch table:
    its "groq" branch incorrectly patches the client as if it were
    Anthropic-shaped (client.messages.create) instead of OpenAI-shaped
    (client.chat.completions.create), which is what Groq's actual API uses.
    Using provider="openai" routes through ragas's correctly-wired OpenAI
    branch while requests still physically go to Groq's servers.
    """
    from openai import OpenAI as OpenAICompatibleClient
    
    # Exclude infrastructure failures from scoring — they measure Groq's
    # rate limit, not the pipeline's actual retrieval/synthesis quality.
    scoreable = [item for item in collected if not item["_rate_limited"]]
    skipped = len(collected) - len(scoreable)
    if skipped:
        print(f"\n⚠️  Excluding {skipped} rate-limited question(s) from RAGAS scoring "
              f"(infrastructure failure, not a pipeline quality signal)")

    if not scoreable:
        raise RuntimeError("No scoreable results — all questions were rate-limited.")


    groq_client = OpenAICompatibleClient(
        api_key=os.getenv("GROQ_API_KEY"),
        base_url="https://api.groq.com/openai/v1",
    )
    judge_llm = llm_factory("llama-3.1-8b-instant", provider="openai", client=groq_client)

    langchain_embeddings = LangchainHFEmbeddings(model_name="all-MiniLM-L6-v2")
    ragas_embeddings = LangchainEmbeddingsWrapper(langchain_embeddings)

    dataset = EvaluationDataset.from_list([
        {
            "user_input": item["question"],
            "response": item["answer"],
            "retrieved_contexts": item["contexts"],
            "reference": item["ground_truth"],
        }
        for item in scoreable 
    ])

    metrics = [
        Faithfulness(llm=judge_llm),
        AnswerRelevancy(llm=judge_llm, embeddings=ragas_embeddings),
        ContextPrecision(llm=judge_llm),
        ContextRecall(llm=judge_llm),
    ]

    print("\nRunning RAGAS evaluation...")
    results = evaluate(
    dataset=dataset,
    metrics=metrics,
    run_config=RunConfig(max_workers=2),
)

    return results


def save_results(collected: list[dict], scores):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    raw_path = os.path.join(RESULTS_DIR, f"raw_results_{timestamp}.json")
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump(collected, f, indent=2, ensure_ascii=False)

    df = scores.to_pandas()

    # Flag any per-question NaNs BEFORE averaging them away
    nan_counts = df.isna().sum()
    if nan_counts.any():
        print("\n⚠️  WARNING — some metric scores are NaN (likely rate limit / quota):")
        print(nan_counts[nan_counts > 0])

    scores_dict = df.mean(numeric_only=True).to_dict()
    scores_path = os.path.join(RESULTS_DIR, f"scores_{timestamp}.json")
    with open(scores_path, "w", encoding="utf-8") as f:
        json.dump(scores_dict, f, indent=2)

    print(f"\nSaved raw results to: {raw_path}")
    print(f"Saved aggregate scores to: {scores_path}")

    return scores_dict


if __name__ == "__main__":
    import sys

    # Optional: scope the whole benchmark run to one document,
    # e.g. python run_evaluation.py "4) gradient descent (GD) and variants.pptx.pdf"
    document_scope = sys.argv[1] if len(sys.argv) > 1 else None
    #BENCHMARK = BENCHMARK[:1]  # TEMP — validate 1 question before full run

    print(f"Running benchmark ({len(BENCHMARK)} questions), scope={document_scope or 'ALL documents'}\n")

    collected = run_pipeline_on_benchmark(document_scope=document_scope)
    scores = score_with_ragas(collected)
    final_scores = save_results(collected, scores)

    print("\n" + "=" * 60)
    print("FINAL RAGAS SCORES")
    print("=" * 60)
    for metric_name, value in final_scores.items():
        print(f"{metric_name}: {value:.4f}")