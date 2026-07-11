# database.py
# Async SQLAlchemy engine + session factory for Neon Postgres.
#
# This is a SEPARATE store from Qdrant. Qdrant still holds vectors/chunks.
# This DB holds relational data: users, document ownership, conversations, messages.
#
# DATABASE_URL comes from .env — get it from the Neon dashboard's "Connection string"
# (use the "Pooled connection" string, not the direct one — HF Spaces containers
# open/close connections frequently, and Neon's pooler handles that better than
# a direct connection would under repeated cold starts).
#
# IMPORTANT: Neon's connection string starts with "postgresql://" — SQLAlchemy's
# async engine needs the asyncpg driver spelled out explicitly, or it'll try to
# use the sync psycopg2 driver and fail. We rewrite the scheme below so you can
# paste Neon's string as-is into .env without editing it by hand.

import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base

load_dotenv()

_raw_url = os.getenv("DATABASE_URL")
if not _raw_url:
    raise RuntimeError(
        "DATABASE_URL is not set. Add it to backend/.env — "
        "get the pooled connection string from your Neon dashboard."
    )

# Rewrite postgresql:// -> postgresql+asyncpg:// if needed (Neon gives you
# the plain postgresql:// form; SQLAlchemy's async engine needs the driver named).
if _raw_url.startswith("postgresql://"):
    DATABASE_URL = _raw_url.replace("postgresql://", "postgresql+asyncpg://", 1)
elif _raw_url.startswith("postgres://"):
    DATABASE_URL = _raw_url.replace("postgres://", "postgresql+asyncpg://", 1)
else:
    DATABASE_URL = _raw_url

# Neon's pooled connection string includes "?sslmode=require" — asyncpg doesn't
# understand that query param (it's a psycopg2-ism), it needs ssl passed as a
# connect arg instead. Strip it from the URL and pass ssl=True via connect_args.
_connect_args = {}
if "sslmode=require" in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.split("?")[0]
    _connect_args["ssl"] = True

engine = create_async_engine(
    DATABASE_URL,
    connect_args=_connect_args,
    pool_pre_ping=True,   # checks connection is alive before using it — avoids
                          # "connection closed" errors after HF Spaces idles out
    echo=False,           # set True temporarily if you need to debug generated SQL
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

Base = declarative_base()


async def get_db():
    """FastAPI dependency — yields a DB session, closes it after the request."""
    async with AsyncSessionLocal() as session:
        yield session


async def init_db():
    """
    Create all tables if they don't exist. Call once at startup (or run
    db/init_db.py manually). This is NOT a substitute for Alembic migrations
    long-term — fine for a portfolio project at this stage, but if you ever
    need to alter a table's columns after data exists, you'll want Alembic
    instead of this (create_all only creates missing tables, it never alters
    existing ones).
    """
    from db import models  # noqa: F401 — import so models register on Base.metadata
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)