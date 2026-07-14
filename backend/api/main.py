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
    # allow_credentials=True is harmless to leave on but no longer load-
    # bearing for auth: the frontend switched from httpOnly cookies to a
    # Bearer token in the Authorization header (see auth/dependencies.py),
    # specifically to sidestep an HF Spaces proxy bug that drops the
    # Access-Control-Allow-Credentials header on preflight requests. Bearer
    # tokens don't use the browser's credentialed-request mode, so this
    # setting simply isn't checked anymore for the auth flow.
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
async def startup_tasks():
    """Combined startup tasks with timeout protection and lazy loading"""
    import asyncio
    
    print("===== Starting application initialization =====")
    
    # Database initialization with timeout
    try:
        print("1/2: Initializing database connection...")
        await asyncio.wait_for(init_db(), timeout=30.0)
        print("✓ Database ready")
    except asyncio.TimeoutError:
        print("⚠ Database initialization timed out - will retry on first request")
    except Exception as e:
        print(f"⚠ Database initialization failed: {e} - will retry on first request")
    
    # LAZY LOAD embedding model instead of preloading
    # This prevents blocking startup - model loads on first /upload or /query request
    print("2/2: Embedding model will load on first use (lazy loading)")
    print("✓ Application ready to accept requests")
    print("===== Startup complete =====")


@app.get("/")
def root():
    """Root endpoint to verify the API is running"""
    return {
        "status": "running",
        "message": "Multi-Agent RAG Research Assistant API",
        "health_check": "/health"
    }


@app.get("/health")
def health_check():
    """Health check endpoint for monitoring services"""
    return {
        "status": "ok",
        "service": "Multi-Agent RAG Research Assistant",
        "version": "0.1.0"
    }