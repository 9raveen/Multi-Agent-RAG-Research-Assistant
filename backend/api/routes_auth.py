# routes_auth.py
# POST /auth/signup, POST /auth/login, POST /auth/logout, GET /auth/me
#
# Auth state travels as an httpOnly cookie, not a bearer token in localStorage —
# JS on the page can't read it, so an XSS bug elsewhere can't steal the session.
# This means the frontend must send fetch requests with `credentials: 'include'`
# for the cookie to actually be attached (covered in the frontend wiring step).

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession
import os

from api.schemas import UserCreate, UserLogin, UserOut
from auth.security import hash_password, verify_password, create_access_token
from auth.dependencies import get_current_user, COOKIE_NAME
from db.database import get_db
from db.crud import get_user_by_email, create_user
from db.models import User

router = APIRouter(prefix="/auth", tags=["auth"])

# Cookie settings shared by login (set) and logout (delete) so they can't drift
# out of sync — a mismatched path/samesite between set and delete means the
# delete silently fails to clear the cookie the browser actually has.
#
# samesite="none" (not "lax"): your frontend (vercel.app) and backend
# (huggingface.co Spaces) are on DIFFERENT domains, so every request from the
# browser to the API is cross-site. SameSite=Lax cookies are only sent on
# same-site requests and top-level navigations — a cross-site fetch() call
# (which is what your frontend does on every API request) would silently NOT
# include the cookie, and every request after login would look logged-out.
# SameSite=None is required for cross-site cookies, and browsers require
# Secure=True whenever SameSite=None is used.
#
# Secure=True requires HTTPS. HF Spaces + Vercel are both HTTPS in prod, so
# leave this on by default. If you're testing locally over plain
# http://localhost, the browser will silently refuse to store a Secure
# cookie — set ENV=local in your .env for that session and this flips
# secure=False so local testing still works. Never do this in prod.
_IS_LOCAL_DEV = os.getenv("ENV") == "local"

_COOKIE_KWARGS = dict(
    key=COOKIE_NAME,
    httponly=True,
    samesite="none" if not _IS_LOCAL_DEV else "lax",
    secure=not _IS_LOCAL_DEV,
    path="/",
)


@router.post("/signup", response_model=UserOut, status_code=201)
async def signup(payload: UserCreate, response: Response, db: AsyncSession = Depends(get_db)):
    existing = await get_user_by_email(db, payload.email)
    if existing:
        raise HTTPException(status_code=409, detail="An account with this email already exists.")

    user = await create_user(db, email=payload.email, hashed_pw=hash_password(payload.password))

    token = create_access_token(str(user.id))
    response.set_cookie(value=token, max_age=60 * 60 * 24, **_COOKIE_KWARGS)

    return UserOut(id=str(user.id), email=user.email)


@router.post("/login", response_model=UserOut)
async def login(payload: UserLogin, response: Response, db: AsyncSession = Depends(get_db)):
    user = await get_user_by_email(db, payload.email)
    if not user or not verify_password(payload.password, user.hashed_pw):
        # Same error for "no such user" and "wrong password" — don't leak
        # which one it was, that tells an attacker whether an email is registered.
        raise HTTPException(status_code=401, detail="Incorrect email or password.")

    token = create_access_token(str(user.id))
    response.set_cookie(value=token, max_age=60 * 60 * 24, **_COOKIE_KWARGS)

    return UserOut(id=str(user.id), email=user.email)


@router.post("/logout", status_code=204)
async def logout(response: Response):
    response.delete_cookie(key=COOKIE_NAME, path="/")


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)):
    return UserOut(id=str(user.id), email=user.email)