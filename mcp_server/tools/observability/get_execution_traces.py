from mcp_server.core.tracer import tracer

async def run(args: dict) -> dict:
    """
    Retrieve structured execution traces from the SQLite database.
    Allows developers to inspect agent-tool interaction history.
    """
    limit = args.get("limit", 20)
    
    try:
        traces = tracer.get_traces(limit=limit)
        return {
            "success": True,
            "data": {
                "traces": traces,
                "count": len(traces)
            },
            "error": None,
            "meta": {
                "limit": limit
            }
        }
    except Exception as e:
        return {
            "success": False,
            "data": None,
            "error": {
                "code": "TRACER_ERROR",
                "message": str(e)
            },
            "meta": {}
        }
