# schemas.py
# Pydantic models define the exact shape of API requests/responses.
# FastAPI uses these for automatic validation + auto-generated docs (/docs).

from pydantic import BaseModel


class QueryRequest(BaseModel):
    query: str
    document_scope: str | None = None


class TraceStep(BaseModel):
    node: str
    revision: int
    rate_limited: bool
    critique_passed: bool | None
    critique_feedback: str | None
    chunks_retrieved: int


class QueryResponse(BaseModel):
    query: str
    document_scope: str | None = None   # optional — filename to restrict search to
    answer: str
    critique_passed: bool
    revisions_taken: int
    sources: list[dict]   # page_number, source_file, chunk_type per retrieved chunk
    trace: list[TraceStep]  # NEW — per-node pipeline trace, powers the agent trace panel


class UploadResponse(BaseModel):
    filename: str
    pages_extracted: int
    chunks_created: int
    tables_detected: int
    vectors_stored: int

class EvaluationResponse(BaseModel):
    scores: dict[str, float]
    question_count: int | None
    timestamp: str