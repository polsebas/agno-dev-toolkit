from rag.storage.milvus_client import MilvusClient

async def run(args: dict) -> dict:
    """
    Simulates querying framework knowledge using Milvus exact vector search.
    """
    query = args.get("query")
    
    if not query:
        return {
            "success": False,
            "data": None,
            "error": {"code": "INVALID_INPUT", "message": "Provide 'query' to search for."},
            "meta": {}
        }
    
    try:
        # Our Milvus implementation connects on init and has a mock search ready
        client = MilvusClient()
        results = client.similarity_search(query=query)
        
        return {
            "success": True,
            "data": {
                "query": query,
                "results": results
            },
            "error": None,
            "meta": {
                "storage": "milvus",
                "result_count": len(results)
            }
        }
    except Exception as e:
        return {
            "success": False,
            "data": None,
            "error": {"code": "MILVUS_ERROR", "message": str(e)},
            "meta": {}
        }
