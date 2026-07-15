# models.py
# SQLAlchemy models — the relational schema from the Phase 8 plan.
#
# UUID primary keys are generated in Python (uuid.uuid4), not via Postgres's
# gen_random_uuid(). This avoids needing to enable the pgcrypto extension on
# Neon — one less thing to configure, and it works identically either way
# since we're not relying on DB-side UUID generation for anything.

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Text, Boolean, Integer, ForeignKey, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.database import Base


def _uuid_col(**kwargs):
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, **kwargs)


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = _uuid_col()
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    hashed_pw: Mapped[str] = mapped_column(String, nullable=False)
    is_guest: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # NEW: marks demo accounts
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    documents: Mapped[list["Document"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    conversations: Mapped[list["Conversation"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = _uuid_col()
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    source_file: Mapped[str] = mapped_column(String, nullable=False)  # matches Qdrant payload's source_file
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    status: Mapped[str] = mapped_column(String, default="ready")  # ready | processing | failed

    user: Mapped["User"] = relationship(back_populates="documents")
    conversations: Mapped[list["Conversation"]] = relationship(back_populates="document")


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = _uuid_col()
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str | None] = mapped_column(String, nullable=True)  # auto-set from first query
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    user: Mapped["User"] = relationship(back_populates="conversations")
    document: Mapped["Document | None"] = relationship(back_populates="conversations")
    messages: Mapped[list["Message"]] = relationship(back_populates="conversation", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = _uuid_col()
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE")
    )
    role: Mapped[str] = mapped_column(String, nullable=False)  # "user" | "assistant"
    content: Mapped[str] = mapped_column(Text, nullable=False)
    sources: Mapped[list | None] = mapped_column(JSON, nullable=True)       # assistant only
    critique_passed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)  # assistant only
    revisions_taken: Mapped[int | None] = mapped_column(Integer, nullable=True)   # assistant only
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")