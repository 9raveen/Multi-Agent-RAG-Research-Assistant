# dependencies.py
# FastAPI dependency that reads the JWT from the httpOnly cookie, validates
# it, and returns the User row. Use as: user: User = Depends(get_current_user)
# in any route that should require login.

from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from auth.security import decode_access_token
from db.database import get_db
from db.crud import get_user_by_id
from db.models import User

COOKIE_NAME = "access_token"


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated.")

    user_id = decode_access_token(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired session.")

    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User no longer exists.")

    return user