# synthesis_agent.py
import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from groq import Groq, RateLimitError
from dotenv import load_dotenv

from retrieval.retriever import format_chunks_for_prompt
from agents.state import ResearchState

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

SYSTEM_PROMPT = """You are a research assistant. Answer the user's question using ONLY the information in the provided context below.

Rules:
- Do not use outside knowledge. If the context doesn't contain enough information to answer, say so explicitly.
- Cite the source for each claim using the page numbers given in the context (e.g. "(page 3)").
- If the context includes a table, you may reference specific rows/values directly.
- Be precise and avoid vague statements. Do not pad the answer with filler.
"""


def synthesis_node(state: ResearchState) -> dict:
    query = state["query"]
    chunks = state["retrieved_chunks"]

    context = format_chunks_for_prompt(chunks)

    user_prompt = f"""Context:
{context}

Question: {query}

Answer using only the context above."""

    print(f"[synthesis_node] generating answer from {len(chunks)} chunks")

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            max_tokens=500,
        )
        answer = response.choices[0].message.content
        rate_limited = False
    except RateLimitError as e:
        print(f"[synthesis_node] RATE LIMIT hit — returning empty answer, no retry. {e}")
        answer = "SYNTHESIS FAILED — Groq rate limit reached before answer could be generated."
        rate_limited = True

    print(f"[synthesis_node] answer: {answer[:200]}...")

    return {
        "synthesis_output": answer,
        "rate_limited": rate_limited,
        "previous_answer": state.get("synthesis_output", ""),  # captures OLD answer, BEFORE this call
    }