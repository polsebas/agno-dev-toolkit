import logging
from typing import List, Dict, Any

import chromadb

from rag.storage.vector_store import VectorStore

logger = logging.getLogger("rag.storage.chroma")


class ChromaStore(VectorStore):
    """
    ChromaDB-backed vector store. Pure Python, no Docker, no network calls.
    Uses PersistentClient for on-disk storage.
    """

    def __init__(self, persist_path: str = "data/chroma_db",
                 collection_name: str = "agno_framework_knowledge"):
        self._persist_path = persist_path
        self._collection_name = collection_name
        self._client: chromadb.ClientAPI | None = None
        self._collection: chromadb.Collection | None = None

    def connect(self) -> None:
        """Initialize PersistentClient pointing at the local directory."""
        self._client = chromadb.PersistentClient(path=self._persist_path)
        logger.info("ChromaDB connected at %s", self._persist_path)

    def create_collection(self, name: str | None = None, dim: int = 384) -> None:
        """
        Get or create a collection. ChromaDB doesn't need explicit dimension
        — it infers from the first insert — but we accept `dim` for API compat.
        """
        if self._client is None:
            self.connect()
        coll_name = name or self._collection_name
        self._collection = self._client.get_or_create_collection(
            name=coll_name,
            metadata={"hnsw:space": "cosine"},  # cosine distance for similarity
        )
        logger.info("Collection '%s' ready (%d items)",
                     coll_name, self._collection.count())

    def insert(self, texts: List[str], vectors: List[List[float]],
               metadata: List[Dict[str, Any]]) -> None:
        """Insert documents with embeddings and metadata."""
        if self._collection is None:
            self.create_collection()

        # ChromaDB requires unique string IDs
        import uuid
        ids = [str(uuid.uuid4()) for _ in texts]

        # ChromaDB metadata values must be str, int, float, or bool
        sanitised_meta = []
        for m in metadata:
            sanitised_meta.append(
                {k: str(v) if not isinstance(v, (str, int, float, bool)) else v
                 for k, v in m.items()}
            )

        self._collection.add(
            ids=ids,
            documents=texts,
            embeddings=vectors,
            metadatas=sanitised_meta,
        )
        logger.info("Inserted %d documents", len(texts))

    def search(self, query_vector: List[float], top_k: int = 5,
               min_score: float = 0.0) -> List[Dict[str, Any]]:
        """
        Query the collection by vector similarity.

        ChromaDB returns distances (cosine distance when configured).
        Convert to similarity: score = 1 - distance  (cosine distance ∈ [0, 2])
        so similarity ∈ [-1, 1] but practically [0, 1] for normalised embeddings.
        """
        if self._collection is None:
            try:
                self.create_collection()
            except Exception:
                return []

        if self._collection.count() == 0:
            return []

        try:
            results = self._collection.query(
                query_embeddings=[query_vector],
                n_results=min(top_k, self._collection.count()),
                include=["documents", "metadatas", "distances"],
            )
        except Exception as e:
            logger.warning("ChromaDB query failed: %s", e)
            return []

        hits = []
        distances = results.get("distances", [[]])[0]
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        ids = results.get("ids", [[]])[0]

        for i, dist in enumerate(distances):
            # Cosine distance → similarity score
            score = 1.0 - dist
            score = max(0.0, min(1.0, score))  # clamp to [0, 1]

            if score >= min_score:
                hit = {
                    "id": ids[i],
                    "score": round(score, 4),
                    "text": documents[i] if i < len(documents) else None,
                    "distance": dist,
                }
                # Merge metadata
                if i < len(metadatas) and metadatas[i]:
                    hit.update(metadatas[i])
                hits.append(hit)

        return hits

    def collection_exists(self, name: str) -> bool:
        """Check if a collection exists."""
        if self._client is None:
            self.connect()
        try:
            existing = [c.name for c in self._client.list_collections()]
            return name in existing
        except Exception:
            return False
