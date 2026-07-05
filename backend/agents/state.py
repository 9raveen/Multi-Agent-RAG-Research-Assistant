# state.py
# Shared state schema for the multi-agent research pipeline.

from typing import TypedDict

class ChatTurn(TypedDict):
    role: str      # "user" | "assistant"
    content: str

class ResearchState(TypedDict):
    query: str                          # the user's question
    rewritten_query: str          # NEW — standalone version of query, used for retrieval
    chat_history: list[ChatTurn]  # NEW — prior turns, capped to last N by the caller
    document_scope: str | None      # ← new: which document to restrict search to
    retrieved_chunks: list[dict]        # raw retrieval hits (text + table, with metadata)
    synthesis_output: str               # LLM-generated answer
    critique_passed: bool
    critique_feedback: str              # WHY it passed/failed — used to steer retry
    revision_count: int
    rate_limited: bool
    previous_answer: str  # NEW — tracks last synthesis output for staleness check
