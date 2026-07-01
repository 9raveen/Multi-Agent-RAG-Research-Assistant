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
#   - Point IDs are DETERMINISTIC (derived from chunk_id), not random —
#     this makes re-running embedder.py on the same PDF idempotent:
#     it overwrites existing points instead of creating duplicates.

from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
)
import uuid
import hashlib


# ── Constants ───────────────────────────────────────────────────────────────

COLLECTION_NAME = "research_documents"
EMBEDDING_DIM   = 384        # all-MiniLM-L6-v2 output dimension
BATCH_SIZE      = 32         # how many chunks to embed + upload at once


# ── Init ────────────────────────────────────────────────────────────────────

embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
qdrant = QdrantClient(host="localhost", port=6333)


# ── Collection Setup ────────────────────────────────────────────────────────

def ensure_collection_exists():
    """
    Create the Qdrant collection if it doesn't already exist.
    Idempotent: safe to call multiple times.
    """
    existing = [c.name for c in qdrant.get_collections().collections]

    if COLLECTION_NAME not in existing:
        qdrant.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(
                size=EMBEDDING_DIM,
                distance=Distance.COSINE
            )
        )
        print(f"Created collection: {COLLECTION_NAME}")
    else:
        print(f"Collection already exists: {COLLECTION_NAME}")


# ── Point ID Generation ──────────────────────────────────────────────────────

def chunk_id_to_point_id(chunk_id: str) -> str:
    """
    Deterministic UUID derived from chunk_id.

    Why: PointStruct previously used uuid.uuid4() (random) for id, which
    meant re-running embedder.py on the same PDF created brand-new points
    every time instead of overwriting the old ones — Qdrant's upsert only
    overwrites when the ID matches exactly. Random IDs never match, so every
    test run silently accumulated duplicate copies of the same chunks.

    Fix: hash chunk_id (which is itself deterministic — same file + same
    page + same chunk index always produces the same chunk_id) into a
    stable UUID. Same content → same point ID → upsert overwrites instead
    of duplicating. Different content → different chunk_id → different
    point ID → no collision.
    """
    return str(uuid.UUID(hashlib.md5(chunk_id.encode()).hexdigest()))


# ── Embedding ───────────────────────────────────────────────────────────────

def embed_chunks(chunks: list[dict]) -> list[dict]:
    """
    Add an 'embedding' field to each chunk by embedding its child text.
    """
    texts = [chunk["text"] for chunk in chunks]

    print(f"Embedding {len(texts)} chunks in batches of {BATCH_SIZE}...")

    embeddings = embedding_model.encode(
        texts,
        batch_size=BATCH_SIZE,
        show_progress_bar=True
    )

    for chunk, embedding in zip(chunks, embeddings):
        chunk["embedding"] = embedding.tolist()

    return chunks


# ── Qdrant Upload ────────────────────────────────────────────────────────────

def upload_to_qdrant(chunks: list[dict]) -> int:
    """
    Upload embedded chunks to Qdrant as points.

    Point ID is now derived deterministically from chunk_id (see
    chunk_id_to_point_id) instead of a random UUID — re-uploading the
    same PDF overwrites existing points rather than duplicating them.
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
            "chunk_type":      chunk["chunk_type"],
        }

        points.append(
            PointStruct(
                id=chunk_id_to_point_id(chunk["chunk_id"]),   # ← deterministic, not random
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