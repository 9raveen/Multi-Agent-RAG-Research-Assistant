# routes_auth.py
# POST /auth/signup, POST /auth/login, POST /auth/logout, GET /auth/me
#
# Bearer token in the response body (not an httpOnly cookie) — see the
# comment at the top of auth/dependencies.py for why: Hugging Face Spaces'
# proxy has an active bug dropping Access-Control-Allow-Credentials on CORS
# preflight, which breaks cookie-based cross-origin auth regardless of how
# correctly this app's own CORS config is set. The frontend stores this
# token (sessionStorage) and sends it as `Authorization: Bearer <token>` on
# every subsequent request.

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import secrets

from api.schemas import UserCreate, UserLogin, UserOut, AuthResponse
from auth.security import hash_password, verify_password, create_access_token
from auth.dependencies import get_current_user
from db.database import get_db
from db.crud import get_user_by_email, create_user
from db.models import User

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=AuthResponse, status_code=201)
async def signup(payload: UserCreate, db: AsyncSession = Depends(get_db)):
    existing = await get_user_by_email(db, payload.email)
    if existing:
        raise HTTPException(status_code=409, detail="An account with this email already exists.")

    user = await create_user(db, email=payload.email, hashed_pw=hash_password(payload.password))
    token = create_access_token(str(user.id))
    is_guest = getattr(user, 'is_guest', False)

    return AuthResponse(id=str(user.id), email=user.email, access_token=token, is_guest=is_guest)


@router.post("/login", response_model=AuthResponse)
async def login(payload: UserLogin, db: AsyncSession = Depends(get_db)):
    user = await get_user_by_email(db, payload.email)
    if not user or not verify_password(payload.password, user.hashed_pw):
        # Same error for "no such user" and "wrong password" — don't leak
        # which one it was, that tells an attacker whether an email is registered.
        raise HTTPException(status_code=401, detail="Incorrect email or password.")

    token = create_access_token(str(user.id))
    is_guest = getattr(user, 'is_guest', False)
    return AuthResponse(id=str(user.id), email=user.email, access_token=token, is_guest=is_guest)


@router.post("/logout", status_code=204)
async def logout():
    # Stateless JWT — there's no server-side session to invalidate here.
    # The frontend just discards its stored token. Endpoint kept for API
    # symmetry and as a hook point if server-side token blacklisting is
    # ever added later.
    return


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)):
    is_guest = getattr(user, 'is_guest', False)  # Safe fallback if column doesn't exist yet
    return UserOut(id=str(user.id), email=user.email, is_guest=is_guest)


@router.post("/guest", response_model=AuthResponse, status_code=201)
async def create_guest_account(db: AsyncSession = Depends(get_db)):
    """
    Create a temporary guest account for demo purposes.
    
    Each guest gets:
    - A unique, random email (guest_<random>@demo.local)
    - A random password (never shown to user, account is ephemeral)
    - Full access to upload PDFs and ask questions
    - Automatic cleanup after 24 hours (via background task)
    - Data isolation (can't see other users' documents)
    
    This showcases the auth/isolation system while allowing instant trial access.
    """
    # Generate unique guest identifier
    guest_id = secrets.token_hex(8)  # 16-character random hex
    guest_email = f"guest_{guest_id}@demo.local"
    guest_password = secrets.token_urlsafe(32)  # Random password, never shown
    
    # Create guest user account
    user = await create_user(
        db, 
        email=guest_email, 
        hashed_pw=hash_password(guest_password),
        is_guest=True
    )
    
    # Generate auth token
    token = create_access_token(str(user.id))
    
    return AuthResponse(
        id=str(user.id), 
        email=user.email, 
        access_token=token,
        is_guest=True  # Explicitly mark this as a guest account
    )