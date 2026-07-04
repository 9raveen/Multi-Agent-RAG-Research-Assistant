# retrieval/embedding_model.py
from sentence_transformers import SentenceTransformer

# Single shared instance — imported by both embedder.py and retriever.py
# to avoid loading the ~300-400MB model twice into memory.
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")