# main.py
# FastAPI app entry point — registers routes, configures CORS.

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from retrieval.embedding_model import get_embedding_model
from api.routes_query import router as query_router
from api.routes_upload import router as upload_router

app = FastAPI(
    title="Multi-Agent RAG Research Assistant",
    description="Upload PDFs, ask questions, get cited answers via a LangGraph research/synthesis/critique pipeline.",
    version="0.1.0",
)
@app.on_event("startup")
async def preload_model():
    print("Pre-loading embedding model at startup...")
    get_embedding_model()
    print("Embedding model ready.")

from api.routes_evaluation import router as evaluation_router
app.include_router(evaluation_router)
# CORS: allows the React frontend (Phase 4, likely running on localhost:3000
# or similar during dev) to call this API from the browser. Wide open for
# now — tighten to specific origins before actual deployment.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(query_router)
app.include_router(upload_router)


@app.get("/health")
def health_check():
    return {"status": "ok"}