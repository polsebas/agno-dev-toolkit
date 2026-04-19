from config.settings import settings
from rag.storage.vector_store import VectorStore


def get_vector_store() -> VectorStore:
    """
    Factory that returns the configured vector store backend.
    Controlled by VECTOR_BACKEND env var (default: 'chroma').
    """
    if settings.vector_backend == "chroma":
        from rag.storage.chroma_backend import ChromaStore
        return ChromaStore(settings.chroma_persist_path, settings.collection_name)
    elif settings.vector_backend == "milvus":
        from rag.storage.milvus_client import MilvusStore
        return MilvusStore(settings.milvus_host, settings.milvus_port,
                           settings.collection_name)
    raise ValueError(f"Unknown vector backend: {settings.vector_backend}")
