# schemas.py
# Pydantic models define the exact shape of API requests/responses.
# FastAPI uses these for automatic validation + auto-generated docs (/docs).

from pydantic import BaseModel, EmailStr


# ── Auth ──────────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: str
    email: str
    is_guest: bool = False  # NEW: indicates if this is a temporary demo account

    class Config:
        from_attributes = True  # lets .from_orm-style construction work off a SQLAlchemy User row


class AuthResponse(BaseModel):
    id: str
    email: str
    access_token: str
    token_type: str = "bearer"
    is_guest: bool = False  # NEW: indicates if this is a temporary demo account


class ChatTurnSchema(BaseModel):
    role: str
    content: str

class QueryRequest(BaseModel):
    query: str
    document_scope: str | None = None
    chat_history: list[ChatTurnSchema] = []  # DEPRECATED (Phase 8): no longer read by
                                               # routes_query.py — history is now loaded
                                               # server-side from Postgres via conversation_id.
                                               # Field kept so older frontend requests that
                                               # still send it don't fail validation; safe
                                               # to stop sending it once the frontend updates.
    conversation_id: str | None = None  # omit to start a new conversation,
                                          # pass an existing id to continue one


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
    conversation_id: str                # NEW (Phase 8) — echoes back the conversation this
                                          # exchange was saved under; capture this on the first
                                          # message of a new chat so follow-ups can pass it in
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


# ── Conversations (Phase 8) ─────────────────────────────────────────────────

class ConversationSummary(BaseModel):
    id: str
    title: str | None
    document_id: str | None
    created_at: str


class MessageOut(BaseModel):
    id: str
    role: str
    content: str
    sources: list | None = None
    critique_passed: bool | None = None
    revisions_taken: int | None = None
    created_at: str


class ConversationDetail(BaseModel):
    id: str
    title: str | None
    document_id: str | None
    created_at: str
    messages: list[MessageOut]