import logging
from typing import List, Dict, Any

from pymilvus import connections, FieldSchema, CollectionSchema, DataType, Collection, utility

from rag.storage.vector_store import VectorStore

logger = logging.getLogger("rag.storage.milvus")

COLLECTION_NAME = "agno_knowledge"


# ---------------------------------------------------------------------------
# Legacy module-level functions (kept for backward compat with pipeline.py)
# ---------------------------------------------------------------------------

def connect():
    connections.connect("default", host="localhost", port="19530")


def create_collection():
    if utility.has_collection(COLLECTION_NAME):
        return Collection(COLLECTION_NAME)

    fields = [
        FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
        FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=384),
        FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65535),
        # metadata
        FieldSchema(name="source", dtype=DataType.VARCHAR, max_length=500),
        FieldSchema(name="framework", dtype=DataType.VARCHAR, max_length=50),
        FieldSchema(name="type", dtype=DataType.VARCHAR, max_length=50),
    ]

    schema = CollectionSchema(fields, "Real RAG Pipeline Knowledge")
    collection = Collection(COLLECTION_NAME, schema)

    # Create index required for search
    index_params = {
        "index_type": "IVF_FLAT",
        "metric_type": "L2",
        "params": {"nlist": 10}
    }
    collection.create_index(field_name="vector", index_params=index_params)
    return collection


def insert_batch(collection, embeddings, texts, sources, frameworks, types):
    collection.insert([
        embeddings,
        texts,
        sources,
        frameworks,
        types
    ])


# ---------------------------------------------------------------------------
# VectorStore-compatible wrapper
# ---------------------------------------------------------------------------

class MilvusStore(VectorStore):
    """Milvus backend implementing the VectorStore ABC."""

    def __init__(self, host: str = "localhost", port: int = 19530,
                 collection_name: str = "agno_framework_knowledge"):
        self._host = host
        self._port = port
        self._collection_name = collection_name
        self._collection = None

    def connect(self) -> None:
        connections.connect("default", host=self._host, port=str(self._port))
        logger.info("Milvus connected at %s:%s", self._host, self._port)

    def create_collection(self, name: str | None = None, dim: int = 384) -> None:
        coll_name = name or self._collection_name
        if utility.has_collection(coll_name):
            self._collection = Collection(coll_name)
        else:
            fields = [
                FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
                FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=dim),
                FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65535),
                FieldSchema(name="source", dtype=DataType.VARCHAR, max_length=500),
                FieldSchema(name="framework", dtype=DataType.VARCHAR, max_length=50),
                FieldSchema(name="type", dtype=DataType.VARCHAR, max_length=50),
            ]
            schema = CollectionSchema(fields, "Agno RAG Knowledge")
            self._collection = Collection(coll_name, schema)
            index_params = {
                "index_type": "IVF_FLAT",
                "metric_type": "L2",
                "params": {"nlist": 10}
            }
            self._collection.create_index(field_name="vector", index_params=index_params)
        self._collection.load()
        logger.info("Milvus collection '%s' ready", coll_name)

    def insert(self, texts: List[str], vectors: List[List[float]],
               metadata: List[Dict[str, Any]]) -> None:
        if self._collection is None:
            self.create_collection()

        sources = [m.get("source", "") for m in metadata]
        frameworks = [m.get("framework", "") for m in metadata]
        types = [m.get("type", "") for m in metadata]

        self._collection.insert([
            vectors,
            texts,
            sources,
            frameworks,
            types,
        ])
        logger.info("Inserted %d documents into Milvus", len(texts))

    def search(self, query_vector: List[float], top_k: int = 5,
               min_score: float = 0.0) -> List[Dict[str, Any]]:
        if self._collection is None:
            try:
                self.create_collection()
            except Exception:
                return []

        search_params = {
            "metric_type": "L2",
            "params": {"nprobe": 10},
        }

        results = self._collection.search(
            data=[query_vector],
            anns_field="vector",
            param=search_params,
            limit=top_k,
            output_fields=["text", "source", "framework"],
        )

        hits = []
        for result_set in results:
            for hit in result_set:
                distance = hit.distance
                # L2 distance → similarity: score = 1 / (1 + distance)
                score = 1.0 / (1.0 + distance)
                if score >= min_score:
                    hits.append({
                        "id": hit.id,
                        "score": round(score, 4),
                        "distance": distance,
                        "text": hit.entity.get("text"),
                        "source": hit.entity.get("source"),
                        "framework": hit.entity.get("framework"),
                    })
        return hits

    def collection_exists(self, name: str) -> bool:
        try:
            return utility.has_collection(name)
        except Exception:
            return False


# ---------------------------------------------------------------------------
# Legacy class kept for any direct imports
# ---------------------------------------------------------------------------

class MilvusClient:
    """Legacy wrapper for query compatibility with MCP server."""

    def __init__(self):
        connect()
        self.collection = create_collection()
        self.collection.load()

    def similarity_search(self, query=None, limit=2):
        from rag.ingestion.embedder import embed
        if not self.collection:
            return []

        search_params = {
            "metric_type": "L2",
            "params": {"nprobe": 10},
        }

        # Real semantic search
        query_vector = embed([query])

        results = self.collection.search(
            data=query_vector,
            anns_field="vector",
            param=search_params,
            limit=limit,
            output_fields=["text", "source", "framework"]
        )

        mapped_results = []
        for hits in results:
            for hit in hits:
                mapped_results.append({
                    "id": hit.id,
                    "distance": hit.distance,
                    "text": hit.entity.get("text"),
                    "source": hit.entity.get("source"),
                    "framework": hit.entity.get("framework")
                })

        return mapped_results
