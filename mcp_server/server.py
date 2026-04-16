from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import json
import time

from mcp_server.core.registry import TOOL_REGISTRY
from mcp_server.core.dispatcher import dispatch_tool

app = FastAPI(title="Agno Dev Toolkit MCP Server")


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

        result = await dispatch_tool(tool_name, arguments)

        latency = int((time.time() - start_time) * 1000)

        result["meta"] = result.get("meta", {})
        result["meta"]["latency_ms"] = latency
        result["meta"]["contract_version"] = "0.1"

        return _mcp_success(result)

    except Exception as e:
        return _mcp_error(str(e))


def _mcp_success(payload: dict):
    return JSONResponse(
        content={
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(payload)
                }
            ],
            "isError": False
        }
    )


def _mcp_error(message: str):
    return JSONResponse(
        content={
            "content": [
                {
                    "type": "text",
                    "text": json.dumps({
                        "success": False,
                        "data": None,
                        "error": {
                            "code": "INTERNAL_ERROR",
                            "message": message
                        },
                        "meta": {}
                    })
                }
            ],
            "isError": True
        }
    )