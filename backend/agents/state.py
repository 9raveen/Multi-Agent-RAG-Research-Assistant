# state.py
# Shared state schema for the multi-agent research pipeline.

from typing import TypedDict


class ResearchState(TypedDict):
    query: str                          # the user's question
    document_scope: str | None      # ← new: which document to restrict search to
    retrieved_chunks: list[dict]        # raw retrieval hits (text + table, with metadata)
    synthesis_output: str               # LLM-generated answer
    critique_passed: bool
    critique_feedback: str              # WHY it passed/failed — used to steer retry
    revision_count: int