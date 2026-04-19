import logging

logger = logging.getLogger("mcp.tool.query_framework_knowledge")


async def run(args: dict) -> dict:
    """
    Retrieve relevant Agno framework patterns from curated test-based
    RAG index backed by Milvus, with graceful degradation.
    """
    query = args.get("query")

    if not query:
        return _error("INVALID_INPUT", "Provide 'query' to search for.")

    top_k = args.get("top_k", 5)
    min_score = args.get("min_score", 0.75)
    version = args.get("version", "auto")

    try:
        from rag.storage.milvus_client import MilvusClient

        client = MilvusClient()
        raw_results = client.similarity_search(query=query, limit=top_k)

        # Filter by min_score (Milvus returns L2 distance — lower is better)
        # Convert L2 distance to a similarity score: score = 1 / (1 + distance)
        results = []
        for hit in raw_results:
            distance = hit.get("distance", float("inf"))
            score = 1.0 / (1.0 + distance)
            if score >= min_score:
                hit["score"] = round(score, 4)
                results.append(hit)

        return {
            "success": True,
            "data": {
                "query": query,
                "results": results,
            },
            "error": None,
            "meta": {
                "storage": "milvus",
                "result_count": len(results),
                "top_k": top_k,
                "min_score": min_score,
                "version": version,
            },
        }

    except ImportError as e:
        logger.warning("Milvus dependencies not installed: %s", e)
        return _error(
            "MILVUS_UNAVAILABLE",
            f"Milvus dependencies are not installed: {e}. "
            "Install pymilvus and sentence-transformers to enable RAG.",
        )
    except ConnectionError as e:
        logger.warning("Milvus connection failed: %s", e)
        return _error(
            "MILVUS_CONNECTION_ERROR",
            f"Cannot connect to Milvus: {e}. "
            "Ensure the Milvus container is running (docker compose up -d).",
        )
    except Exception as e:
        logger.exception("Error in query_framework_knowledge")
        return _error("MILVUS_ERROR", str(e))


def _error(code: str, message: str) -> dict:
    return {
        "success": False,
        "data": None,
        "error": {"code": code, "message": message},
        "meta": {},
    }
