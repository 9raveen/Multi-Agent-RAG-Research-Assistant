# test_stream.py — place in backend/, delete after checking
from agents.graph import build_graph

graph = build_graph()

initial_state = {
    "query": "What is gradient descent?",
    "document_scope": "4) gradient descent (GD) and variants.pptx.pdf",
    "retrieved_chunks": [],
    "synthesis_output": "",
    "critique_passed": False,
    "critique_feedback": "",
    "revision_count": 0,
    "rate_limited": False,
    "previous_answer": "",
}

for step in graph.stream(initial_state):
    print(step)
    print("---")