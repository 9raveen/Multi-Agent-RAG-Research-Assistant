# routes_conversations.py
# GET /conversations       — list the logged-in user's past conversations (sidebar)
# GET /conversations/{id}  — full message history for one conversation

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas import ConversationSummary, ConversationDetail, MessageOut
from auth.dependencies import get_current_user
from db.database import get_db
from db.crud import list_conversations, get_conversation_with_messages
from db.models import User

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("", response_model=list[ConversationSummary])
async def get_conversations(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    conversations = await list_conversations(db, user.id)
    return [
        ConversationSummary(
            id=str(c.id),
            title=c.title,
            document_id=str(c.document_id) if c.document_id else None,
            created_at=c.created_at.isoformat(),
        )
        for c in conversations
    ]


@router.get("/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(
    conversation_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await get_conversation_with_messages(db, user.id, conversation_id)
    if not result:
        # Covers "doesn't exist" and "belongs to another user" identically —
        # don't leak which one it is.
        raise HTTPException(status_code=404, detail="Conversation not found.")

    convo, messages = result
    return ConversationDetail(
        id=str(convo.id),
        title=convo.title,
        document_id=str(convo.document_id) if convo.document_id else None,
        created_at=convo.created_at.isoformat(),
        messages=[
            MessageOut(
                id=str(m.id),
                role=m.role,
                content=m.content,
                sources=m.sources,
                critique_passed=m.critique_passed,
                revisions_taken=m.revisions_taken,
                created_at=m.created_at.isoformat(),
            )
            for m in messages
        ],
    )