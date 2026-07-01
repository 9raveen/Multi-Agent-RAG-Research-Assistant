# retriever.py
# Responsibility: Query Qdrant for relevant chunks given a text query.
# Embeds the query with the SAME model used during ingestion (all-MiniLM-L6-v2)
# — using a different model here would produce an incompatible vector space.

from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient

COLLECTION_NAME = "research_documents"

embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
qdrant = QdrantClient(host="localhost", port=6333)


def retrieve(query: str, top_k: int = 5) -> list[dict]:
    """
    Embed the query and search Qdrant for the top_k most similar chunks.

    Returns raw payload dicts (not formatted strings) — formatting is
    handled separately so callers can choose raw vs formatted as needed.
    """
    query_vector = embedding_model.encode(query).tolist()

    response = qdrant.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        limit=top_k,
    )

    results = []
    for hit in response.points:
        payload = hit.payload
        results.append({
            "text": payload["text"],
            "parent_text": payload["parent_text"],
            "page_number": payload["page_number"],
            "source_file": payload["source_file"],
            "section_header": payload["section_header"],
            "chunk_id": payload["chunk_id"],
            "chunk_type": payload.get("chunk_type", "text"),
            "score": hit.score,
        })

    return results


def format_chunks_for_prompt(chunks: list[dict]) -> str:
    """
    Turn retrieved chunks into a single string block for LLM context injection.
    Tables and text are formatted differently — a table hit is prefixed and
    kept as markdown so the LLM can actually read row/column structure;
    plain prose is injected as-is.
    """
    blocks = []

    for i, chunk in enumerate(chunks, start=1):
        source_line = f"[Source {i}: {chunk['source_file']}, page {chunk['page_number']}, section: {chunk['section_header']}]"

        if chunk["chunk_type"] == "table":
            content = f"Retrieved table:\n{chunk['parent_text']}"
        else:
            content = chunk["parent_text"]  # use parent for fuller context

        blocks.append(f"{source_line}\n{content}")

    return "\n\n---\n\n".join(blocks)


# ── Quick test ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python retriever.py <query text>")
        sys.exit(1)

    query = sys.argv[1]
    results = retrieve(query, top_k=5)

    print(f"Query: {query}")
    print(f"Retrieved {len(results)} chunks\n")

    for r in results:
        print(f"[{r['chunk_type']}] score={r['score']:.3f} page={r['page_number']} chunk_id={r['chunk_id']}")
        print(r["text"][:150])
        print("---")

    print("\n--- Formatted for prompt ---")
    print(format_chunks_for_prompt(results))