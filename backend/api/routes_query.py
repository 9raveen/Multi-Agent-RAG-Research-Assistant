# routes_query.py
# POST /query — runs the full LangGraph research pipeline for a given question.

import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from fastapi import APIRouter, HTTPException

from api.schemas import QueryRequest, QueryResponse
from agents.graph import build_graph

router = APIRouter()

# Build the graph once at module load — compiling is relatively expensive,
# no need to redo it on every request.
graph = build_graph()


@router.post("/query", response_model=QueryResponse)
def run_query(request: QueryRequest):
    if not request.query or not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    initial_state = {
        "query": request.query,
        "document_scope": request.document_scope,
        "retrieved_chunks": [],
        "synthesis_output": "",
        "critique_passed": False,
        "critique_feedback": "",
        "revision_count": 0,
    }

    try:
        result = graph.invoke(initial_state)
    except Exception as e:
        # Covers Qdrant/Groq connection failures, etc. — surfaced as 500,
        # not a silent crash, so the frontend can show a real error message.
        raise HTTPException(status_code=500, detail=f"Pipeline execution failed: {str(e)}")

    sources = [
        {
            "page_number": chunk["page_number"],
            "source_file": chunk["source_file"],
            "chunk_type": chunk["chunk_type"],
        }
        for chunk in result["retrieved_chunks"]
    ]

    return QueryResponse(
        query=result["query"],
        document_scope=request.document_scope,
        answer=result["synthesis_output"],
        critique_passed=result["critique_passed"],
        revisions_taken=result["revision_count"],
        sources=sources,
    )