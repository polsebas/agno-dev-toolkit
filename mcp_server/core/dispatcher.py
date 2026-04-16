import importlib


async def dispatch_tool(tool_name: str, arguments: dict):
    module_path = __import_path(tool_name)

    module = importlib.import_module(module_path)

    if not hasattr(module, "run"):
        return _error("TOOL_MISSING_RUN", f"{tool_name} has no run()")

    try:
        result = await module.run(arguments)
        return result

    except Exception as e:
        return _error("TOOL_EXECUTION_ERROR", str(e))


def __import_path(tool_name: str) -> str:
    from mcp_server.core.registry import TOOL_REGISTRY
    return TOOL_REGISTRY[tool_name]


def _error(code: str, message: str):
    return {
        "success": False,
        "data": None,
        "error": {
            "code": code,
            "message": message
        },
        "meta": {}
    }