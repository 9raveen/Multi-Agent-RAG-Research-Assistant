# research_agent.py
# Node responsibility: retrieve relevant chunks from Qdrant for the current query.
# Uses rewritten_query (standalone form, resolved from chat history by
# rewrite_query_node) for retrieval — this is what makes follow-up questions
# like "what about SGD instead?" retrieve correctly instead of failing on
# an ambiguous, context-dependent query.

import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from retrieval.retriever import retrieve, retrieve_all_chunks
from agents.state import ResearchState

# Keyword-based detection, not an extra LLM call — cheap, fast, deterministic,
# and good enough for this: a false negative just means a summary-style
# request gets answered as a normal Q&A instead (a real, still-thorough
# answer, just built from top-k chunks rather than the whole document).
# A false positive is rarer with these specific phrasings and mainly costs
# an unnecessary full-document fetch, not a wrong-looking answer.
SUMMARY_KEYWORDS = [
    "summarize", "summarise", "summary of", "give me a summary",
    "tl;dr", "tldr", "give a tldr",
    "overview of the document", "overview of this document",
    "what is this document about", "what's this document about",
    "what is this paper about", "what's this paper about",
]


def is_summary_request(query: str) -> bool:
    q = query.lower()
    return any(kw in q for kw in SUMMARY_KEYWORDS)


def research_node(state: ResearchState) -> dict:
    # Use rewritten_query if present (set by rewrite_query_node before this
    # node runs); fall back to raw query only as a safety net, e.g. if the
    # graph is ever invoked without going through rewrite_query_node first.
    search_query = state.get("rewritten_query") or state["query"]
    document_scope = state.get("document_scope")
    user_id = state.get("user_id")  # NEW (Phase 8) — scopes retrieval to the logged-in user
    revision_count = state.get("revision_count", 0)

    # Summarization only makes sense when scoped to ONE specific document —
    # "summarize" across an unscoped multi-document search has no well-
    # defined target, so that combination falls through to normal retrieval.
    summary_request = is_summary_request(state["query"]) and bool(document_scope)

    if summary_request:
        print(f"[research_node] summary request detected — fetching ALL chunks for '{document_scope}'")
        chunks = retrieve_all_chunks(document_scope, user_id=user_id)
    else:
        # On retry, keep the SAME resolved query for retrieval — don't concatenate
        # growing critique feedback into it. Feedback sentences are natural-language
        # explanations, not search terms, and stuffing them into the query dilutes
        # the embedding vector's similarity signal (confirmed: caused context_precision
        # to drop from 0.82 -> 0.58 across a 10-question run with two retry-heavy questions).
        # Widening top_k alone gives retrieval more candidates to work with on retry,
        # which is a cleaner lever than mutating the query text.
        top_k = 8 if revision_count == 0 else 10  # was 5/8 — bumped for fuller answers;
                                                     # re-run RAGAS after this to confirm
                                                     # context_precision holds up

        print(f"[research_node] attempt={revision_count + 1}, query='{search_query}', top_k={top_k}")
        chunks = retrieve(search_query, top_k=top_k, source_file=document_scope, user_id=user_id)

    print(f"[research_node] retrieved {len(chunks)} chunks")

    return {"retrieved_chunks": chunks, "is_summary_request": summary_request}