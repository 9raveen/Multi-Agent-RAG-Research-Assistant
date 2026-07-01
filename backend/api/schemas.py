# schemas.py
# Pydantic models define the exact shape of API requests/responses.
# FastAPI uses these for automatic validation + auto-generated docs (/docs).

from pydantic import BaseModel


class QueryRequest(BaseModel):
    query: str


class QueryResponse(BaseModel):
    query: str
    answer: str
    critique_passed: bool
    revisions_taken: int
    sources: list[dict]   # page_number, source_file, chunk_type per retrieved chunk


class UploadResponse(BaseModel):
    filename: str
    pages_extracted: int
    chunks_created: int
    tables_detected: int
    vectors_stored: int