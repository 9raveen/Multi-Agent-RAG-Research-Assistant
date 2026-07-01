# critique_agent.py
# Node responsibility: check whether synthesis_output is fully supported by
# retrieved_chunks and actually answers the query. Returns structured JSON
# (passed/feedback) so routing can act on it without regex-parsing free text.

import sys, os, json
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from groq import Groq
from dotenv import load_dotenv

from retrieval.retriever import format_chunks_for_prompt
from agents.state import ResearchState

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

CRITIQUE_SYSTEM_PROMPT = """You are a strict fact-checker reviewing an AI-generated answer against its source context.

Evaluate:
1. Is every claim in the answer actually supported by the provided context? (no hallucination)
2. Does the answer fully address the question asked?

Respond ONLY with valid JSON in this exact format, nothing else:
{"passed": true or false, "feedback": "one sentence explaining what's missing or wrong, or 'looks good' if passed"}
"""


def critique_node(state: ResearchState) -> dict:
    query = state["query"]
    answer = state["synthesis_output"]
    chunks = state["retrieved_chunks"]
    revision_count = state.get("revision_count", 0) + 1

    context = format_chunks_for_prompt(chunks)

    user_prompt = f"""Context:
{context}

Question: {query}

Generated Answer: {answer}

Evaluate this answer."""

    print(f"[critique_node] reviewing answer (revision {revision_count})")

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": CRITIQUE_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.0,  # deterministic — this is a judgment call, not creative
    )

    raw = response.choices[0].message.content.strip()

    # Fail-safe parsing: if the LLM doesn't return clean JSON, default to
    # passed=False rather than blindly accepting a possibly-bad answer.
    try:
        # Strip markdown code fences if the model wrapped the JSON in ```json ... ```
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