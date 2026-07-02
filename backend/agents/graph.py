# graph.py
# Wires the three agent nodes into a LangGraph pipeline with a conditional
# retry loop: research -> synthesis -> critique -> (done | retry | give_up)

import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from langgraph.graph import StateGraph, START, END

from agents.state import ResearchState
from agents.research_agent import research_node
from agents.synthesis_agent import synthesis_node
from agents.critique_agent import critique_node

MAX_REVISIONS = 3


def route_after_critique(state: ResearchState) -> str:
    if state["critique_passed"]:
        return "done"
    elif state["revision_count"] >= MAX_REVISIONS:
        return "give_up"
    else:
        return "retry"


def build_graph():
    builder = StateGraph(ResearchState)

    builder.add_node("research_node", research_node)
    builder.add_node("synthesis_node", synthesis_node)
    builder.add_node("critique_node", critique_node)

    builder.add_edge(START, "research_node")
    builder.add_edge("research_node", "synthesis_node")
    builder.add_edge("synthesis_node", "critique_node")

    builder.add_conditional_edges(
        "critique_node",
        route_after_critique,
        {
            "done": END,
            "retry": "research_node",
            "give_up": END,
        },
    )

    return builder.compile()


# ── Quick test ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python graph.py '<question>' [document_scope]")
        sys.exit(1)

    query = sys.argv[1]
    document_scope = sys.argv[2] if len(sys.argv) > 2 else None

    graph = build_graph()

    initial_state = {
        "query": query,
        "document_scope": document_scope,
        "retrieved_chunks": [],
        "synthesis_output": "",
        "critique_passed": False,
        "critique_feedback": "",
        "revision_count": 0,
    }

    result = graph.invoke(initial_state)

    print("\n" + "=" * 60)
    print("FINAL RESULT")
    print("=" * 60)
    print(f"Query: {result['query']}")
    print(f"Revisions taken: {result['revision_count']}")
    print(f"Critique passed: {result['critique_passed']}")
    print(f"\nAnswer:\n{result['synthesis_output']}")