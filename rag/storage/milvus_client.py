import uuid
import random
from pymilvus import connections, FieldSchema, CollectionSchema, DataType, Collection, utility

COLLECTION_NAME = "agno_knowledge"

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

class MilvusClient:
    """Legacy wrapper for query compatibility with MCP server"""
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
