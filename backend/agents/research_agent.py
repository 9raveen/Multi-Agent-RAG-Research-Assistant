# research_agent.py
# Node responsibility: retrieve relevant chunks from Qdrant for the current query.
# On retry (revision_count > 0), incorporates critique_feedback into the search
# so the retry actually looks for different/better evidence, not the same thing again.

import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from retrieval.retriever import retrieve
from agents.state import ResearchState


def research_node(state: ResearchState) -> dict:
    query = state["query"]
    document_scope = state.get("document_scope")
    revision_count = state.get("revision_count", 0)
    feedback = state.get("critique_feedback", "")

    # On retry, keep the ORIGINAL query for retrieval — don't concatenate
    # growing critique feedback into it. Feedback sentences are natural-language
    # explanations, not search terms, and stuffing them into the query dilutes
    # the embedding vector's similarity signal (confirmed: caused context_precision
    # to drop from 0.82 -> 0.58 across a 10-question run with two retry-heavy questions).
    # Widening top_k alone gives retrieval more candidates to work with on retry,
    # which is a cleaner lever than mutating the query text.
    search_query = query
    top_k = 5 if revision_count == 0 else 8

    print(f"[research_node] attempt={revision_count + 1}, query='{search_query}', top_k={top_k}")

    chunks = retrieve(search_query, top_k=top_k, source_file=document_scope)

    print(f"[research_node] retrieved {len(chunks)} chunks")

    return {"retrieved_chunks": chunks}