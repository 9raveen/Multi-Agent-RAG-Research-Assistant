# crud.py
# Small DB helper functions — kept separate from routes so routes stay
# focused on HTTP concerns and these stay focused on queries.

import uuid
import asyncio
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import AsyncSessionLocal
from db.models import User, Document, Conversation, Message

# A single shared executor used by run_sync().
# Each submitted task creates its own event loop inside the worker thread,
# fully isolated from Uvicorn's event loop — safe for HTTP/2 keep-alive
# connections where the same OS thread may be reused across multiple requests.
_DB_EXECUTOR = ThreadPoolExecutor(max_workers=4, thread_name_prefix="crud-sync")


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: str) -> User | None:
    try:
        uid = uuid.UUID(user_id)
    except ValueError:
        return None
    result = await db.execute(select(User).where(User.id == uid))
    return result.scalar_one_or_none()


async def create_user(db: AsyncSession, email: str, hashed_pw: str, is_guest: bool = False) -> User:
    user = User(email=email, hashed_pw=hashed_pw, is_guest=is_guest)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def create_document(db: AsyncSession, user_id: uuid.UUID, source_file: str) -> Document:
    document = Document(user_id=user_id, source_file=source_file, status="ready")
    db.add(document)
    await db.commit()
    await db.refresh(document)
    return document


# ── Conversations & Messages (Phase 8) ──────────────────────────────────────
#
# routes_query.py's /query and /query/stream are sync `def` routes (the
# LangGraph pipeline underneath is blocking, not async) — FastAPI runs sync
# routes in a worker thread. run_sync() below uses a dedicated executor so
# each DB call gets its own isolated event loop, fully decoupled from
# Uvicorn's loop. This prevents ERR_HTTP2_PROTOCOL_ERROR on follow-up
# messages where the same OS thread may be reused across requests.
# They open their OWN db session rather than reusing one injected via
# Depends(get_db), since an AsyncSession created in the request's event
# loop can't safely be awaited from a different thread/loop.
#
# Everywhere else (routes_conversations.py, an async route) — use the
# `_async` functions directly with a Depends(get_db) session, same pattern
# as create_user/create_document above.

def run_sync(coro):
    """
    Run an async coroutine synchronously from a sync context.

    Uses a dedicated ThreadPoolExecutor so each call gets a fresh event loop
    in a worker thread that is completely isolated from Uvicorn's own loop.
    This is safe to call from a streaming generator on an HTTP/2 connection
    where asyncio.run() would raise "This event loop is already running".
    """
    def _run_in_new_loop():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()
            asyncio.set_event_loop(None)

    future = _DB_EXECUTOR.submit(_run_in_new_loop)
    return future.result()


async def _get_document_id_for_scope(db: AsyncSession, user_id: uuid.UUID, source_file: str | None) -> uuid.UUID | None:
    if not source_file:
        return None
    result = await db.execute(
        select(Document)
        .where(Document.user_id == user_id, Document.source_file == source_file)
        .order_by(desc(Document.uploaded_at))
        .limit(1)
    )
    doc = result.scalar_one_or_none()
    return doc.id if doc else None


async def _get_document_scope_for_conversation(db: AsyncSession, conversation: Conversation) -> str | None:
    """Get the document filename for a conversation from its document_id."""
    if not conversation.document_id:
        return None
    result = await db.execute(
        select(Document).where(Document.id == conversation.document_id)
    )
    doc = result.scalar_one_or_none()
    return doc.source_file if doc else None


async def _get_or_create_conversation_async(
    db: AsyncSession,
    user_id: uuid.UUID,
    conversation_id: str | None,
    document_scope: str | None,
    first_query: str,
) -> Conversation:
    if conversation_id:
        try:
            cid = uuid.UUID(conversation_id)
        except ValueError:
            raise ValueError("Malformed conversation_id.")
        result = await db.execute(
            select(Conversation).where(Conversation.id == cid, Conversation.user_id == user_id)
        )
        convo = result.scalar_one_or_none()
        if not convo:
            # Either it doesn't exist, or it belongs to someone else — same
            # error either way, don't reveal which (avoids confirming another
            # user's conversation IDs exist).
            raise ValueError("Conversation not found.")
        return convo

    document_id = await _get_document_id_for_scope(db, user_id, document_scope)
    title = (first_query[:60] + "…") if len(first_query) > 60 else first_query
    convo = Conversation(user_id=user_id, document_id=document_id, title=title)
    db.add(convo)
    await db.commit()
    await db.refresh(convo)
    return convo


async def _add_message_async(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    role: str,
    content: str,
    sources: list | None = None,
    critique_passed: bool | None = None,
    revisions_taken: int | None = None,
) -> Message:
    message = Message(
        conversation_id=conversation_id,
        role=role,
        content=content,
        sources=sources,
        critique_passed=critique_passed,
        revisions_taken=revisions_taken,
    )
    db.add(message)
    await db.commit()
    await db.refresh(message)
    return message


def get_or_create_conversation_sync(
    user_id: uuid.UUID, conversation_id: str | None, document_scope: str | None, first_query: str
) -> Conversation:
    async def _run():
        async with AsyncSessionLocal() as db:
            return await _get_or_create_conversation_async(db, user_id, conversation_id, document_scope, first_query)
    return run_sync(_run())


def add_message_sync(
    conversation_id: uuid.UUID,
    role: str,
    content: str,
    sources: list | None = None,
    critique_passed: bool | None = None,
    revisions_taken: int | None = None,
) -> Message:
    async def _run():
        async with AsyncSessionLocal() as db:
            return await _add_message_async(db, conversation_id, role, content, sources, critique_passed, revisions_taken)
    return run_sync(_run())


CHAT_HISTORY_MAX_TURNS = 10  # last 10 messages (~5 exchanges) — caps context size/cost,
                              # same cap the original design intended the caller to apply


async def _get_chat_history_async(db: AsyncSession, conversation_id: uuid.UUID) -> list[dict]:
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(desc(Message.created_at))
        .limit(CHAT_HISTORY_MAX_TURNS)
    )
    messages = list(result.scalars().all())
    messages.reverse()  # query pulled newest-first (for the LIMIT to keep the *most recent*
                          # turns); pipeline needs oldest-first chronological order
    return [{"role": m.role, "content": m.content} for m in messages]


def get_chat_history_sync(conversation_id: uuid.UUID) -> list[dict]:
    """
    Server-authoritative chat history (Phase 8): pulls prior turns straight
    from Postgres rather than trusting whatever the client sent in the
    request body. Call this BEFORE add_message_sync() for the current turn,
    so the current query isn't double-counted as its own history.
    """
    async def _run():
        async with AsyncSessionLocal() as db:
            return await _get_chat_history_async(db, conversation_id)
    return run_sync(_run())


async def list_conversations(db: AsyncSession, user_id: uuid.UUID) -> list[Conversation]:
    result = await db.execute(
        select(Conversation).where(Conversation.user_id == user_id).order_by(desc(Conversation.created_at))
    )
    return list(result.scalars().all())


async def get_conversation_with_messages(
    db: AsyncSession, user_id: uuid.UUID, conversation_id: str
) -> tuple[Conversation, list[Message]] | None:
    try:
        cid = uuid.UUID(conversation_id)
    except ValueError:
        return None
    result = await db.execute(
        select(Conversation).where(Conversation.id == cid, Conversation.user_id == user_id)
    )
    convo = result.scalar_one_or_none()
    if not convo:
        return None
    msg_result = await db.execute(
        select(Message).where(Message.conversation_id == cid).order_by(Message.created_at)
    )
    # Returned as a separate list rather than assigned to convo.messages —
    # assigning directly to a SQLAlchemy relationship attribute marks it as
    # ORM-managed state (dirty-tracked), which is unnecessary here since we're
    # only reading, not modifying, the conversation's message collection.
    messages = list(msg_result.scalars().all())
    return convo, messages