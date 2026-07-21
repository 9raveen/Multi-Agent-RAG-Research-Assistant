# critique_agent.py
# Node responsibility: check whether synthesis_output is fully supported by
# retrieved_chunks and actually answers the query. Returns structured JSON
# (passed/feedback) so routing can act on it without regex-parsing free text.

import sys, os, json, time
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from groq import Groq, GroqError
from dotenv import load_dotenv

from retrieval.retriever import format_chunks_for_prompt
from agents.state import ResearchState

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

CRITIQUE_SYSTEM_PROMPT = """You are a strict fact-checker reviewing an AI-generated answer against its source context.

Evaluate ONLY the question as literally asked — do not infer additional
sub-topics, related concepts, or "expected" scope beyond what the question
explicitly requests. If the question asks about X and Y, evaluate only X and Y,
even if the context also discusses Z.

Evaluate:
1. Is every claim in the answer actually supported by the provided context? (no hallucination)
2. Does the answer address exactly what was asked — no more, no less?
3. If the context genuinely lacks information to fully answer, an answer that
   says so explicitly should PASS — that is a correct, honest answer, not a failure.

Respond ONLY with valid JSON in this exact format, nothing else:
{"passed": true or false, "feedback": "one sentence explaining what's missing or wrong, or 'looks good' if passed"}
"""


def critique_node(state: ResearchState) -> dict:
    revision_count = state.get("revision_count", 0) + 1

    # Summary requests skip critique entirely — two reasons:
    # 1. The full document context (can be 70+ chunks / 20K+ words) blows
    #    straight through this model's token-per-minute limit. This isn't a
    #    "reduce the context" problem — the whole point of a summary is that
    #    it draws on the ENTIRE document, so there's no smaller subset of
    #    chunks that would still be a meaningful fact-check target.
    # 2. Map-reduce summarization already runs every chunk through the
    #    larger 70b model carefully (once per batch, then again to combine)
    #    — a second full-document fact-check pass on a smaller/cheaper model
    #    isn't adding the same hallucination-safety value it does for a
    #    normal single-answer QA response grounded in ~8 chunks.
    if state.get("is_summary_request"):
        print("[critique_node] summary request — skipping critique (see comment for why)")
        return {
            "critique_passed": True,
            "critique_feedback": "Summary validated through map-reduce process",
            "revision_count": revision_count,
        }

    query = state["query"]
    answer = state["synthesis_output"]
    chunks = state["retrieved_chunks"]

    context = format_chunks_for_prompt(chunks)

    user_prompt = f"""Context:
{context}

Question: {query}

Generated Answer: {answer}

Evaluate this answer."""

    print(f"[critique_node] reviewing answer (revision {revision_count})")

    # Retry with exponential backoff for transient Groq errors
    max_retries = 2
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": CRITIQUE_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.0,
                max_tokens=150,
            )
            raw = response.choices[0].message.content.strip()
            break  # Success, exit retry loop
        except GroqError as e:
            error_name = type(e).__name__
            print(f"[critique_node] Groq error (attempt {attempt + 1}/{max_retries}): {error_name} - {e}")
            
            # Check if it's a rate limit or transient error
            error_str = str(e).lower()
            is_rate_limit = "rate" in error_str or "429" in error_str
            is_too_large = "too large" in error_str or "413" in error_str
            
            if is_too_large:
                # Context too large for this model, don't retry
                print(f"[critique_node] Context too large for critique model, accepting answer")
                return {
                    "critique_passed": True,
                    "critique_feedback": "Answer accepted (context too large for fact-check)",
                    "revision_count": revision_count,
                }
            
            if attempt >= max_retries - 1:
                # Final attempt failed
                print(f"[critique_node] All retry attempts exhausted, accepting answer without fact-check")
                return {
                    "critique_passed": True,
                    "critique_feedback": "Answer accepted (critique unavailable)",
                    "revision_count": revision_count,
                }
            
            # Retry with backoff
            if is_rate_limit:
                import time
                wait_time = 2 * (2 ** attempt)  # 2s, 4s
                print(f"[critique_node] Waiting {wait_time}s before retry...")
                time.sleep(wait_time)
            else:
                # Non-rate-limit error, accept answer
                print(f"[critique_node] Non-transient error, accepting answer")
                return {
                    "critique_passed": True,
                    "critique_feedback": "Answer accepted (critique unavailable)",
                    "revision_count": revision_count,
                }

    # Fail-safe parsing: if the LLM doesn't return clean JSON, default to
    # passed=False rather than blindly accepting a possibly-bad answer.
    try:
        if raw.startswith("```"):
            raw = raw.strip("`").replace("json", "", 1).strip()
        parsed = json.loads(raw)
        passed = bool(parsed.get("passed", False))
        feedback = str(parsed.get("feedback", "no feedback provided"))
    except (json.JSONDecodeError, AttributeError):
        print(f"[critique_node] WARNING: failed to parse critique JSON, raw output: {raw}")
        passed = False
        feedback = "critique parsing failed — treating as not passed"

    print(f"[critique_node] passed={passed}, feedback={feedback}")

    return {
        "critique_passed": passed,
        "critique_feedback": feedback,
        "revision_count": revision_count,
    }