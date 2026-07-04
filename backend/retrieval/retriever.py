# retriever.py
# Responsibility: Query Qdrant for relevant chunks given a text query.
# Embeds the query with the SAME model used during ingestion (all-MiniLM-L6-v2)
# — using a different model here would produce an incompatible vector space.
#
# Embedding model is lazy-loaded via get_embedding_model() — shared with
# embedder.py through retrieval/embedding_model.py, so the model loads
# only once across the whole app, not once per module.

from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
import os
from dotenv import load_dotenv
from retrieval.embedding_model import get_embedding_model

load_dotenv()

COLLECTION_NAME = "research_documents"

# Qdrant Cloud connection — was QdrantClient(host="localhost", port=6333)
qdrant = QdrantClient(
    url=os.getenv("QDRANT_URL"),
    api_key=os.getenv("QDRANT_API_KEY"),
)


def retrieve(query: str, top_k: int = 5, source_file: str | None = None) -> list[dict]:
    """
    Embed the query and search Qdrant for the top_k most similar chunks.
    If source_file is given, restricts search to only chunks from that document
    — prevents cross-document contamination (e.g. asking about doc A and
    getting answers pulled from an unrelated doc B sitting in the same collection).
    """
    model = get_embedding_model()  # lazy load — reuses the same instance embedder.py loaded
    query_vector = list(model.embed([query]))[0].tolist()

    query_filter = None
    if source_file:
        query_filter = Filter(
            must=[FieldCondition(key="source_file", match=MatchValue(value=source_file))]
        )

    response = qdrant.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        query_filter=query_filter,
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
            content = chunk["parent_text"]
        blocks.append(f"{source_line}\n{content}")
    return "\n\n---\n\n".join(blocks)


# ── Quick test ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python retriever.py <query text> [source_file]")
        sys.exit(1)

    query = sys.argv[1]
    source_file = sys.argv[2] if len(sys.argv) > 2 else None

    results = retrieve(query, top_k=5, source_file=source_file)

    print(f"Query: {query}")
    print(f"Scoped to: {source_file or 'ALL documents'}")
    print(f"Retrieved {len(results)} chunks\n")

    for r in results:
        print(f"[{r['chunk_type']}] score={r['score']:.3f} source={r['source_file']} page={r['page_number']}")
        print(r["text"][:150])
        print("---")

    print("\n--- Formatted for prompt ---")
    print(format_chunks_for_prompt(results))