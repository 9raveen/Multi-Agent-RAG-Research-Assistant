# routes_query.py
# POST /query — runs the full LangGraph research pipeline for a given question.
import json
from fastapi.responses import StreamingResponse
from groq import RateLimitError
from agents.query_rewrite_agent import rewrite_query_node
from agents.research_agent import research_node
from agents.synthesis_agent import synthesize_stream
from agents.critique_agent import critique_node
from agents.graph import route_after_critique  # reuse existing retry rules — do not duplicate

import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from fastapi import APIRouter, HTTPException

from api.schemas import QueryRequest, QueryResponse
from agents.graph import build_graph

router = APIRouter()

# Build the graph once at module load — compiling is relatively expensive,
# no need to redo it on every request.
graph = build_graph()

def _sse_event(event_type: str, data: dict) -> str:
    return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"

@router.post("/query/stream")
def run_query(request: QueryRequest):
    if not request.query or not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")
    def event_generator():
        state = {
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
        is_retry = False

        # Rewrite happens once, before the loop — no-op on first turn, same as /query
        state.update(rewrite_query_node(state))

    while True:
            if is_retry:
                yield _sse_event("retry", {"revision": state["revision_count"]})

            # Research — fast, non-streaming, same node used by /query
            state.update(research_node(state))
            trace.append({
                "node": "research_node",
                "revision": state.get("revision_count", 0),
                "rate_limited": state.get("rate_limited", False),
                "critique_passed": state.get("critique_passed"),
                "critique_feedback": state.get("critique_feedback"),
                "chunks_retrieved": len(state.get("retrieved_chunks", [])),
            })

            # Synthesis — STREAM tokens as they arrive
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

            # Critique — fast, non-streaming (needs the full text anyway)
            state.update(critique_node(state))
            trace.append({
                "node": "critique_node", "revision": state.get("revision_count", 0),
                "rate_limited": state.get("rate_limited", False),
                "critique_passed": state.get("critique_passed"),
                "critique_feedback": state.get("critique_feedback"),
                "chunks_retrieved": len(state.get("retrieved_chunks", [])),
            })

            # Reuse the SAME retry rules as the graph — do not reimplement them here
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
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # prevents some reverse proxies from buffering SSE — matters given past HF Spaces/Render infra surprises this project has hit
        },
    )