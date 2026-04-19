import json
import logging
import time

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from mcp_server.core.registry import TOOL_REGISTRY
from mcp_server.core.dispatcher import dispatch_tool

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("mcp.server")

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(title="Agno Dev Toolkit MCP Server")


# ---------------------------------------------------------------------------
# Health & discovery
# ---------------------------------------------------------------------------
@app.get("/health")
async def health():
    """Returns server status and list of registered tools."""
    return {
        "status": "ok",
        "tools": list(TOOL_REGISTRY.keys()),
        "tool_count": len(TOOL_REGISTRY),
    }


@app.get("/tools")
async def tools_schema():
    """Returns the full MCP tool schema for IDE auto-discovery."""
    import os

    schema_path = os.path.join(os.path.dirname(__file__), "..", "mcp.json")
    schema_path = os.path.abspath(schema_path)

    if not os.path.exists(schema_path):
        return JSONResponse(
            status_code=404,
            content={"error": "mcp.json not found"},
        )

    with open(schema_path, "r", encoding="utf-8") as f:
        schema = json.load(f)

    return schema


# ---------------------------------------------------------------------------
# MCP endpoint
# ---------------------------------------------------------------------------
@app.post("/mcp")
async def mcp_endpoint(request: Request):
    start_time = time.time()

    try:
        body = await request.json()

        tool_name = body.get("tool")
        arguments = body.get("arguments", {})

        if not tool_name:
            return _mcp_error("Missing 'tool' field")

        if tool_name not in TOOL_REGISTRY:
            return _mcp_error(f"Unknown tool: {tool_name}")

        logger.info("Dispatching tool: %s", tool_name)
        result = await dispatch_tool(tool_name, arguments)

        latency = int((time.time() - start_time) * 1000)

        result["meta"] = result.get("meta", {})
        result["meta"]["latency_ms"] = latency
        result["meta"]["contract_version"] = "0.1"

        return _mcp_success(result)

    except Exception as e:
        logger.exception("Unhandled error in /mcp endpoint")
        return _mcp_error(str(e))


# ---------------------------------------------------------------------------
# MCP response helpers
# ---------------------------------------------------------------------------
def _mcp_success(payload: dict):
    return JSONResponse(
        content={
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(payload),
                }
            ],
            "isError": False,
        }
    )


def _mcp_error(message: str):
    return JSONResponse(
        content={
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(
                        {
                            "success": False,
                            "data": None,
                            "error": {
                                "code": "INTERNAL_ERROR",
                                "message": message,
                            },
                            "meta": {},
                        }
                    ),
                }
            ],
            "isError": True,
        }
    )