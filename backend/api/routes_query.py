# routes_query.py
# POST /query — non-streaming full-pipeline endpoint (used by run_evaluation.py, /docs testing).
# POST /query/stream — SSE streaming endpoint (used by the live chat UI).

import sys, os, json
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from groq import RateLimitError

from api.schemas import QueryRequest, QueryResponse
from agents.graph import build_graph, route_after_critique
from agents.query_rewrite_agent import rewrite_query_node
from agents.research_agent import research_node
from agents.synthesis_agent import synthesize_stream
from agents.critique_agent import critique_node
from auth.dependencies import get_current_user
from db.models import User

router = APIRouter()

# Build the graph once at module load — compiling is relatively expensive,
# no need to redo it on every request. Used only by the non-streaming /query route.
graph = build_graph()


@router.post("/query", response_model=QueryResponse)
def run_query(request: QueryRequest, user: User = Depends(get_current_user)):
    if not request.query or not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    initial_state = {
        "query": request.query,
        "rewritten_query": "",
        "chat_history": [t.dict() for t in request.chat_history],
        "document_scope": request.document_scope,
        "user_id": str(user.id),
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
        {"page_number": c["page_number"], "source_file": c["source_file"], "chunk_type": c["chunk_type"]}
        for c in final_state["retrieved_chunks"]
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


def _sse_event(event_type: str, data: dict) -> str:
    return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"


@router.post("/query/stream")
def run_query_stream(request: QueryRequest, user: User = Depends(get_current_user)):
    if not request.query or not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    def event_generator():
        state = {
            "query": request.query,
            "rewritten_query": "",
            "chat_history": [t.dict() for t in request.chat_history],
            "document_scope": request.document_scope,
            "user_id": str(user.id),
            "retrieved_chunks": [],
            "synthesis_output": "",
            "critique_passed": False,
            "critique_feedback": "",
            "revision_count": 0,
            "rate_limited": False,
            "previous_answer": "",
        }

        trace = []
        is_retry = False

        state.update(rewrite_query_node(state))

        while True:
            if is_retry:
                yield _sse_event("retry", {"revision": state["revision_count"]})

            state.update(research_node(state))
            trace.append({
                "node": "research_node",
                "revision": state.get("revision_count", 0),
                "rate_limited": state.get("rate_limited", False),
                "critique_passed": state.get("critique_passed"),
                "critique_feedback": state.get("critique_feedback"),
                "chunks_retrieved": len(state.get("retrieved_chunks", [])),
            })

            accumulated = ""
            try:
                search_query = state.get("rewritten_query") or state["query"]
                for token in synthesize_stream(search_query, state["retrieved_chunks"]):
                    accumulated += token
                    yield _sse_event("token", {"text": token})
                state["previous_answer"] = state["synthesis_output"]
                state["synthesis_output"] = accumulated
                state["rate_limited"] = False
            except RateLimitError:
                state["rate_limited"] = True
                state["synthesis_output"] = "SYNTHESIS FAILED — Groq rate limit reached before answer could be generated."
                trace.append({
                    "node": "synthesis_node", "revision": state.get("revision_count", 0),
                    "rate_limited": True, "critique_passed": state.get("critique_passed"),
                    "critique_feedback": state.get("critique_feedback"),
                    "chunks_retrieved": len(state.get("retrieved_chunks", [])),
                })
                yield _sse_event("error", {"message": "Groq rate limit reached"})
                break

            trace.append({
                "node": "synthesis_node", "revision": state.get("revision_count", 0),
                "rate_limited": False, "critique_passed": state.get("critique_passed"),
                "critique_feedback": state.get("critique_feedback"),
                "chunks_retrieved": len(state.get("retrieved_chunks", [])),
            })

            state.update(critique_node(state))
            trace.append({
                "node": "critique_node", "revision": state.get("revision_count", 0),
                "rate_limited": state.get("rate_limited", False),
                "critique_passed": state.get("critique_passed"),
                "critique_feedback": state.get("critique_feedback"),
                "chunks_retrieved": len(state.get("retrieved_chunks", [])),
            })

            route = route_after_critique(state)
            if route in ("done", "give_up"):
                break
            is_retry = True

        sources = [
            {"page_number": c["page_number"], "source_file": c["source_file"], "chunk_type": c["chunk_type"]}
            for c in state["retrieved_chunks"]
        ]

        yield _sse_event("done", {
            "answer": state["synthesis_output"],
            "critique_passed": state["critique_passed"],
            "revisions_taken": state["revision_count"],
            "sources": sources,
            "trace": trace,
        })

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )