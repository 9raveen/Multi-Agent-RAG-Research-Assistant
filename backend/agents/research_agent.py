# research_agent.py
# Node responsibility: retrieve relevant chunks from Qdrant for the current query.
# Uses rewritten_query (standalone form, resolved from chat history by
# rewrite_query_node) for retrieval — this is what makes follow-up questions
# like "what about SGD instead?" retrieve correctly instead of failing on
# an ambiguous, context-dependent query.

import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from retrieval.retriever import retrieve
from agents.state import ResearchState


def research_node(state: ResearchState) -> dict:
    # Use rewritten_query if present (set by rewrite_query_node before this
    # node runs); fall back to raw query only as a safety net, e.g. if the
    # graph is ever invoked without going through rewrite_query_node first.
    search_query = state.get("rewritten_query") or state["query"]
    document_scope = state.get("document_scope")
    revision_count = state.get("revision_count", 0)

    # On retry, keep the SAME resolved query for retrieval — don't concatenate
    # growing critique feedback into it. Feedback sentences are natural-language
    # explanations, not search terms, and stuffing them into the query dilutes
    # the embedding vector's similarity signal (confirmed: caused context_precision
    # to drop from 0.82 -> 0.58 across a 10-question run with two retry-heavy questions).
    # Widening top_k alone gives retrieval more candidates to work with on retry,
    # which is a cleaner lever than mutating the query text.
    top_k = 5 if revision_count == 0 else 8

    print(f"[research_node] attempt={revision_count + 1}, query='{search_query}', top_k={top_k}")

    chunks = retrieve(search_query, top_k=top_k, source_file=document_scope)

    print(f"[research_node] retrieved {len(chunks)} chunks")

    return {"retrieved_chunks": chunks}