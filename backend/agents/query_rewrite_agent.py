# query_rewrite_agent.py
# Node responsibility: rewrite a follow-up question into a standalone question
# using recent chat history, so retrieval doesn't fail on pronouns/references
# ("what about SGD instead?", "explain that more").
#
# Runs BEFORE research_node. If there's no chat history (first turn), it's a
# no-op — rewritten_query just equals query, at zero extra cost.

import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from groq import Groq, RateLimitError
from dotenv import load_dotenv
from agents.state import ResearchState

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

REWRITE_SYSTEM_PROMPT = """You rewrite follow-up questions into standalone questions
using conversation history. Resolve pronouns and references ("it", "that", "instead",
"the second one") into explicit terms from the history.

Rules:
- If the question is already standalone (no references to prior turns), return it UNCHANGED.
- Never answer the question — only rewrite it.
- Output ONLY the rewritten question, nothing else — no explanation, no quotes.
"""


def rewrite_query_node(state: ResearchState) -> dict:
    query = state["query"]
    chat_history = state.get("chat_history", [])

    # No history = first turn = nothing to rewrite. Zero-cost no-op.
    if not chat_history:
        return {"rewritten_query": query}

    # Cap history injected into the prompt to the last 2 exchanges (4 turns)
    # to bound token cost as conversations grow longer.
    recent_history = chat_history[-4:]
    history_text = "\n".join(f"{t['role']}: {t['content']}" for t in recent_history)

    user_prompt = f"""Conversation history:
{history_text}

Follow-up question: "{query}"

Rewrite as a standalone question."""

    print(f"[rewrite_query_node] rewriting: '{query}'")

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",  # cheap model — this is a simple rewriting task
            messages=[
                {"role": "system", "content": REWRITE_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.0,
            max_tokens=100,
        )
        rewritten = response.choices[0].message.content.strip()
    except RateLimitError as e:
        # Fail-safe: fall back to the original query rather than crashing the
        # whole turn. Worse retrieval on this one turn is better than no answer.
        print(f"[rewrite_query_node] RATE LIMIT hit — falling back to original query. {e}")
        rewritten = query

    print(f"[rewrite_query_node] rewritten: '{rewritten}'")

    return {"rewritten_query": rewritten}