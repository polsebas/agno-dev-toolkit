import logging

from config.settings import settings

logger = logging.getLogger("mcp.tool.query_framework_knowledge")


async def run(args: dict) -> dict:
    """
    Retrieve relevant Agno framework patterns from curated test-based
    RAG index, with graceful degradation. Supports both ChromaDB and Milvus
    backends via the factory.
    """
    query = args.get("query")

    if not query:
        return _error("INVALID_INPUT", "Provide 'query' to search for.")

    top_k = args.get("top_k", 5)
    min_score = args.get("min_score", 0.50)
    version = args.get("version", "auto")

    try:
        from rag.storage.factory import get_vector_store
        from rag.ingestion.embedder import embed

        store = get_vector_store()
        store.connect()
        store.create_collection()

        # Embed the query
        query_vector = embed([query])[0]

        # Search using the abstract interface
        results = store.search(
            query_vector=query_vector, top_k=top_k, min_score=min_score
        )

        return {
            "success": True,
            "data": {
                "query": query,
                "results": results,
            },
            "error": None,
            "meta": {
                "storage": settings.vector_backend,
                "result_count": len(results),
                "top_k": top_k,
                "min_score": min_score,
                "version": version,
            },
        }

    except ImportError as e:
        logger.warning("Vector store dependencies not installed: %s", e)
        return _error(
            "VECTOR_STORE_UNAVAILABLE",
            f"Vector store dependencies are not installed: {e}. "
            f"Install the required packages for '{settings.vector_backend}' backend.",
        )
    except ConnectionError as e:
        logger.warning("Vector store connection failed: %s", e)
        return _error(
            "VECTOR_STORE_CONNECTION_ERROR",
            f"Cannot connect to vector store: {e}.",
        )
    except Exception as e:
        logger.exception("Error in query_framework_knowledge")
        return _error("VECTOR_STORE_ERROR", str(e))


def _error(code: str, message: str) -> dict:
    return {
        "success": False,
        "data": None,
        "error": {"code": code, "message": message},
        "meta": {},
    }
