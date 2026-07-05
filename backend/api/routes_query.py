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
        "rewritten_query": "",                                    # NEW
        "chat_history": [t.dict() for t in request.chat_history],  # NEW
        "document_scope": request.document_scope,
        "retrieved_chunks": [],
        "synthesis_output": "",
        "critique_passed": False,
        "critique_feedback": "",
        "revision_count": 0,
        "rate_limited": False,
        "previous_answer": "",
    }

    trace = []
    cumulative_state = dict(initial_state)
    final_state = None

    try:
        for step_output in graph.stream(initial_state):
            for node_name, node_state in step_output.items():
                cumulative_state.update(node_state)
                # Only log trace entries for the 3 main pipeline nodes —
                # rewrite_query_node is a pre-processing step, not part of
                # the visible agent trace panel's story.
                if node_name != "rewrite_query_node":
                    trace.append({
                        "node": node_name,
                        "revision": cumulative_state.get("revision_count", 0),
                        "rate_limited": cumulative_state.get("rate_limited", False),
                        "critique_passed": cumulative_state.get("critique_passed"),
                        "critique_feedback": cumulative_state.get("critique_feedback"),
                        "chunks_retrieved": len(cumulative_state.get("retrieved_chunks", [])),
                    })
                final_state = cumulative_state
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline execution failed: {str(e)}")

    if final_state is None:
        raise HTTPException(status_code=500, detail="Pipeline produced no output.")

    sources = [
        {
            "page_number": chunk["page_number"],
            "source_file": chunk["source_file"],
            "chunk_type": chunk["chunk_type"],
        }
        for chunk in final_state["retrieved_chunks"]
    ]

    return QueryResponse(
        query=final_state["query"],
        document_scope=request.document_scope,
        answer=final_state["synthesis_output"],
        critique_passed=final_state["critique_passed"],
        revisions_taken=final_state["revision_count"],
        sources=sources,
        trace=trace,
    )
        # .stream() instead of .invoke() — captures each node's output as it
        # fires, including every retry attempt, not just the final result.
        # Needed for the agent trace panel; .invoke() collapses intermediate
        # states and would only show the last thing that happened.