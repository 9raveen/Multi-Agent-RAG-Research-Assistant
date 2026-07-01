# embedder.py
# Responsibility: Embed chunks and store them in Qdrant.
#
# Flow:
#   chunks → embed child text → push vector + full metadata to Qdrant
#
# Key design decisions:
#   - Only the child "text" gets embedded (small, precise)
#   - parent_text travels as payload (not embedded)
#   - We batch embed for efficiency (not one-by-one API calls)
#   - Collection is created if it doesn't exist (idempotent)

from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
)
import uuid


# ── Constants ───────────────────────────────────────────────────────────────

COLLECTION_NAME = "research_documents"
EMBEDDING_DIM   = 384        # all-MiniLM-L6-v2 output dimension
BATCH_SIZE      = 32         # how many chunks to embed + upload at once


# ── Init ────────────────────────────────────────────────────────────────────

# Load embedding model once at module level (expensive to reload per call)
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

# Connect to local Qdrant instance
qdrant = QdrantClient(host="localhost", port=6333)


# ── Collection Setup ────────────────────────────────────────────────────────

def ensure_collection_exists():
    """
    Create the Qdrant collection if it doesn't already exist.

    A collection in Qdrant = a table in SQL.
    We define:
        - vector size (must match embedding model output = 384)
        - distance metric (Cosine = standard for semantic similarity)

    Idempotent: safe to call multiple times.
    """
    existing = [c.name for c in qdrant.get_collections().collections]

    if COLLECTION_NAME not in existing:
        qdrant.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(
                size=EMBEDDING_DIM,
                distance=Distance.COSINE  # cosine similarity for semantic search
            )
        )
        print(f"Created collection: {COLLECTION_NAME}")
    else:
        print(f"Collection already exists: {COLLECTION_NAME}")


# ── Embedding ───────────────────────────────────────────────────────────────

def embed_chunks(chunks: list[dict]) -> list[dict]:
    """
    Add an 'embedding' field to each chunk by embedding its child text.

    Args:
        chunks: Output from chunk_pages()

    Returns:
        Same chunks with 'embedding' field added:
        [
            {
                ...existing fields...,
                "embedding": [0.023, -0.045, 0.011, ...]  # 384 floats
            }
        ]

    Why batch?
        SentenceTransformer.encode() processes a list at once using
        matrix operations — much faster than calling encode() in a loop.
    """
    texts = [chunk["text"] for chunk in chunks]  # extract child texts

    print(f"Embedding {len(texts)} chunks in batches of {BATCH_SIZE}...")

    # encode() returns a numpy array of shape (num_chunks, 384)
    embeddings = embedding_model.encode(
        texts,
        batch_size=BATCH_SIZE,
        show_progress_bar=True  # shows a progress bar in terminal
    )

    # Attach embedding back to each chunk dict
    for chunk, embedding in zip(chunks, embeddings):
        chunk["embedding"] = embedding.tolist()  # numpy → plain Python list for JSON serialization

    return chunks


# ── Qdrant Upload ────────────────────────────────────────────────────────────

def upload_to_qdrant(chunks: list[dict]) -> int:
    """
    Upload embedded chunks to Qdrant as points.
    ...
    """
    points = []

    for chunk in chunks:
        payload = {
            "text":            chunk["text"],
            "parent_text":     chunk["parent_text"],
            "page_number":     chunk["page_number"],
            "source_file":     chunk["source_file"],
            "section_header":  chunk["section_header"],
            "chunk_id":        chunk["chunk_id"],
            "parent_chunk_id": chunk["parent_chunk_id"],
            "chunk_index":     chunk["chunk_index"],
            "chunk_type":      chunk["chunk_type"],   # ← new: "text" or "table"
        }

        points.append(
            PointStruct(
                id=str(uuid.uuid4()),
                vector=chunk["embedding"],
                payload=payload
            )
        )

    for i in range(0, len(points), BATCH_SIZE):
        batch = points[i : i + BATCH_SIZE]
        qdrant.upsert(
            collection_name=COLLECTION_NAME,
            points=batch
        )

    print(f"Uploaded {len(points)} points to Qdrant collection '{COLLECTION_NAME}'")
    return len(points)

# ── Main Pipeline Function ───────────────────────────────────────────────────

def embed_and_store(chunks: list[dict]) -> int:
    """
    Full pipeline: ensure collection → embed → upload.

    This is the function called by routes_upload.py later.

    Args:
        chunks: Output from chunk_pages()

    Returns:
        Number of points stored in Qdrant
    """
    ensure_collection_exists()
    chunks_with_embeddings = embed_chunks(chunks)
    count = upload_to_qdrant(chunks_with_embeddings)
    return count


# ── Quick test ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    import os

    sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
    from ingestion.pdf_parser import parse_pdf
    from ingestion.chunker   import chunk_pages

    if len(sys.argv) < 2:
        print("Usage: python embedder.py <path_to_pdf>")
        sys.exit(1)

    # Full ingestion pipeline
    print("Step 1: Parsing PDF...")
    pages = parse_pdf(sys.argv[1])
    print(f"  → {len(pages)} pages extracted")

    print("Step 2: Chunking...")
    chunks = chunk_pages(pages)
    print(f"  → {len(chunks)} chunks created")

    print("Step 3: Embedding + storing in Qdrant...")
    count = embed_and_store(chunks)

    print(f"\n✓ Done. {count} vectors stored in Qdrant.")
    print(f"  Open http://localhost:6333/dashboard → Collections → {COLLECTION_NAME}")
    print(f"  You should see {count} points.")