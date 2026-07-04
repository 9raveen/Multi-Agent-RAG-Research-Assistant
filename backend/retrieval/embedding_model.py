from fastembed import TextEmbedding

_model = None

def get_embedding_model():
    global _model
    if _model is None:
        _model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")  # 384-dim, comparable to MiniLM
    return _model