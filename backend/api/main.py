# main.py
# FastAPI app entry point — registers routes, configures CORS.

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from retrieval.embedding_model import get_embedding_model

from api.routes_query import router as query_router
from api.routes_upload import router as upload_router
from api.routes_evaluation import router as evaluation_router

app = FastAPI(
    title="Multi-Agent RAG Research Assistant",
    description="Upload PDFs, ask questions, get cited answers via a LangGraph research/synthesis/critique pipeline.",
    version="0.1.0",
)

# CORS: allow the deployed Vercel frontend (production + preview URLs).
# No trailing slash on the origin — browsers send Origin without one,
# so a trailing slash here would silently fail to match.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://multi-agent-rag-research-assistant.vercel.app"],
    allow_origin_regex=r"https://multi-agent-rag-research-assistant-.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(query_router)
app.include_router(upload_router)
app.include_router(evaluation_router)


@app.on_event("startup")
async def preload_model():
    print("Pre-loading embedding model at startup...")
    get_embedding_model()
    print("Embedding model ready.")


@app.get("/health")
def health_check():
    return {"status": "ok"}