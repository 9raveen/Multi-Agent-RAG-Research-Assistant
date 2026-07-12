# crud.py
# Small DB helper functions — kept separate from routes so routes stay
# focused on HTTP concerns and these stay focused on queries.

import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import User, Document


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


async def create_user(db: AsyncSession, email: str, hashed_pw: str) -> User:
    user = User(email=email, hashed_pw=hashed_pw)
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