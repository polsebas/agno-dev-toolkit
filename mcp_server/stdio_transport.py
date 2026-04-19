"""
MCP stdio transport for Agno Dev Toolkit.

This module provides a stdio-based MCP server entry point that wraps
the existing dispatcher. It enables IDE integration with Cursor, Claude Code,
and other MCP-compatible editors that communicate with subprocess servers
over stdin/stdout.

Usage:
    python -m mcp_server.stdio_transport
"""

import asyncio
import json
import logging
import os
import sys

# --- GLOBAL STDOUT & LOGGING HARDENING ---
# 1. Capture original stdout for the MCP protocol BEFORE any redirection
_mcp_stdout = sys.stdout
# 2. Redirect sys.stdout to sys.stderr globally to catch library prints/noise
# This ensures stdout stays clean for JSON-RPC, while prints are visible in console
sys.stdout = sys.stderr

# 3. Environment control
os.environ["CHROMA_TELEMETRY_OFF"] = "True"
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "0"

# 4. Configure logging to stderr
log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("mcp.stdio")
# ----------------------------------------

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from mcp_server.core.dispatcher import dispatch_tool
from mcp_server.core.registry import TOOL_REGISTRY


# ---------------------------------------------------------------------------
# Load tool schemas from mcp.json
# ---------------------------------------------------------------------------

def _load_tool_schemas() -> dict:
    """Parse mcp.json and return a dict keyed by tool name."""
    mcp_json_path = os.path.join(
        os.path.dirname(__file__), "..", "mcp.json"
    )
    mcp_json_path = os.path.abspath(mcp_json_path)

    if not os.path.exists(mcp_json_path):
        logger.warning("mcp.json not found at %s", mcp_json_path)
        return {}

    with open(mcp_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    schemas = {}
    for tool_def in data.get("tools", []):
        name = tool_def.get("name")
        if name:
            schemas[name] = tool_def
    return schemas


TOOL_SCHEMAS = _load_tool_schemas()


# ---------------------------------------------------------------------------
# Build MCP Server
# ---------------------------------------------------------------------------

server = Server("agno-dev-toolkit")


@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    """Dynamically list all tools from the registry with schemas from mcp.json."""
    logger.info("MCP Request: list_tools")
    tools = []
    for tool_name in TOOL_REGISTRY:
        schema = TOOL_SCHEMAS.get(tool_name, {})
        tools.append(
            Tool(
                name=tool_name,
                description=schema.get(
                    "description",
                    f"Tool: {tool_name}"
                ),
                inputSchema=schema.get("input_schema", {
                    "type": "object",
                    "properties": {},
                }),
            )
        )
    return tools


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict | None) -> list[TextContent]:
    """
    Dispatch a tool call to the existing dispatcher.
    Errors from dispatch_tool() are returned as MCP text content, not exceptions.
    """
    logger.info("MCP Request: call_tool(name=%s, arguments=%s)", name, arguments)
    if name not in TOOL_REGISTRY:
        return [
            TextContent(
                type="text",
                text=json.dumps({
                    "success": False,
                    "data": None,
                    "error": {
                        "code": "TOOL_NOT_FOUND",
                        "message": f"Tool '{name}' is not registered",
                    },
                    "meta": {},
                }),
            )
        ]

    result = await dispatch_tool(name, arguments or {})

    return [
        TextContent(
            type="text",
            text=json.dumps(result, default=str),
        )
    ]


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def main():
    logger.info(
        "Starting Agno Dev Toolkit MCP stdio server with %d tools",
        len(TOOL_REGISTRY),
    )
    # Restore stdout briefly so stdio_server captures the real FD 1 for binary protocol
    sys.stdout = _mcp_stdout
    try:
        async with stdio_server() as (read_stream, write_stream):
            # Redirect stdout back to stderr so library prints during execution go to logs
            sys.stdout = sys.stderr
            await server.run(
                read_stream,
                write_stream,
                server.create_initialization_options(),
            )
    finally:
        sys.stdout = sys.stderr


if __name__ == "__main__":
    asyncio.run(main())
