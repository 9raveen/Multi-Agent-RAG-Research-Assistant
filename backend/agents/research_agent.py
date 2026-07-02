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

    # On retry, append feedback to the search query so retrieval targets
    # the gap the critique identified, instead of repeating the same search.
    search_query = query
    if revision_count > 0 and feedback:
        search_query = f"{query} {feedback}"

    # Widen the search slightly on retries — more candidates to work with.
    top_k = 5 if revision_count == 0 else 8

    print(f"[research_node] attempt={revision_count + 1}, query='{search_query}', top_k={top_k}")

    chunks = retrieve(search_query, top_k=top_k, source_file=document_scope)

    print(f"[research_node] retrieved {len(chunks)} chunks")

    return {"retrieved_chunks": chunks}