# dependencies.py
# FastAPI dependency that reads the JWT from the Authorization header,
# validates it, and returns the User row. Use as:
#   user: User = Depends(get_current_user)
# in any route that should require login.
#
# Bearer-token-in-header (not an httpOnly cookie) is a deliberate choice for
# this deployment specifically: Hugging Face Spaces' front proxy has an
# active, unresolved bug where it answers CORS preflight (OPTIONS) requests
# itself and drops the Access-Control-Allow-Credentials header — which
# breaks cookie-based cross-origin auth (Vercel frontend → HF Spaces
# backend) no matter how correctly the app's own CORS config is set up.
# A bearer token in the Authorization header never triggers the browser's
# credentialed-request preflight check in the first place, so this sidesteps
# the platform bug entirely rather than depending on HF fixing it.

from fastapi import Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession

from auth.security import decode_access_token
from db.database import get_db
from db.crud import get_user_by_id
from db.models import User


async def get_current_user(
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated.")

    token = authorization.removeprefix("Bearer ").strip()

    user_id = decode_access_token(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired session.")

    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User no longer exists.")

    return user