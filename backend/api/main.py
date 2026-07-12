# main.py
# FastAPI app entry point — registers routes, configures CORS.

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from retrieval.embedding_model import get_embedding_model

from api.routes_query import router as query_router
from api.routes_upload import router as upload_router
from api.routes_evaluation import router as evaluation_router
from api.routes_auth import router as auth_router
from api.routes_conversations import router as conversations_router
from db.database import init_db

app = FastAPI(
    title="Multi-Agent RAG Research Assistant",
    description="Upload PDFs, ask questions, get cited answers via a LangGraph research/synthesis/critique pipeline.",
    version="0.1.0",
)

# CORS: allow the deployed Vercel frontend (production + preview URLs).
# No trailing slash on any origin — browsers send Origin without one,
# so a trailing slash here would silently fail to match.
#
# localhost origins added for local dev (`npm run dev` defaults to 5173,
# but Vite falls back to 5174/5175 etc. if 5173 is already taken — listing
# a few common fallbacks so this doesn't break on a random free port).
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://multi-agent-rag-research-assistant.vercel.app",
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://127.0.0.1:5173",
    ],
    allow_origin_regex=r"https://multi-agent-rag-research-assistant-.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(query_router)
app.include_router(upload_router)
app.include_router(evaluation_router)
app.include_router(auth_router)
app.include_router(conversations_router)


@app.on_event("startup")
async def preload_model():
    print("Pre-loading embedding model at startup...")
    get_embedding_model()
    print("Embedding model ready.")


@app.on_event("startup")
async def create_db_tables():
    # Idempotent — create_all only creates tables that don't already exist.
    # Fine to leave running on every startup at this stage of the project.
    print("Ensuring DB tables exist...")
    await init_db()
    print("DB tables ready.")


@app.get("/health")
def health_check():
    return {"status": "ok"}