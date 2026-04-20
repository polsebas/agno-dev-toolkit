import asyncio
import importlib
import inspect
import logging
import time
from config.settings import settings

logger = logging.getLogger("mcp.dispatcher")


async def dispatch_tool(tool_name: str, arguments: dict) -> dict:
    """
    Dynamically imports and executes a tool module by name.
    Never raises — always returns a structured result dict.
    """
    start = time.time()

    # Resolve import path
    try:
        module_path = _import_path(tool_name)
    except KeyError:
        logger.error("Tool '%s' not found in registry", tool_name)
        return _error("TOOL_NOT_FOUND", f"Tool '{tool_name}' is not registered")

    # Import the module
    try:
        module = importlib.import_module(module_path)
    except ModuleNotFoundError as e:
        logger.error("Module import failed for '%s': %s", tool_name, e)
        return _error("MODULE_NOT_FOUND", f"Cannot import module for '{tool_name}': {e}")
    except Exception as e:
        logger.error("Unexpected import error for '%s': %s", tool_name, e)
        return _error("MODULE_IMPORT_ERROR", f"Import error for '{tool_name}': {e}")

    # Check run() exists
    if not hasattr(module, "run"):
        logger.error("Tool '%s' has no run() function", tool_name)
        return _error("TOOL_MISSING_RUN", f"'{tool_name}' has no run() function")

    run_fn = module.run

    # Execute the tool
    try:
        if inspect.iscoroutinefunction(run_fn):
            result = await asyncio.wait_for(
                run_fn(arguments), timeout=settings.mcp_tool_timeout
            )
        else:
            loop = asyncio.get_event_loop()
            result = await asyncio.wait_for(
                loop.run_in_executor(None, run_fn, arguments),
                timeout=settings.mcp_tool_timeout
            )

        elapsed = int((time.time() - start) * 1000)
        logger.info("Tool '%s' completed in %dms (success=%s)",
                     tool_name, elapsed, result.get("success"))
        return result

    except asyncio.TimeoutError:
        elapsed = int((time.time() - start) * 1000)
        logger.error("Tool '%s' timed out after %dms", tool_name, elapsed)
        return {
            "success": False,
            "data": None,
            "error": {
                "code": "TOOL_TIMEOUT",
                "message": f"Tool exceeded {settings.mcp_tool_timeout}s timeout",
                "tool": tool_name
            },
            "meta": {}
        }
    except Exception as e:
        elapsed = int((time.time() - start) * 1000)
        logger.error("Tool '%s' crashed after %dms: %s", tool_name, elapsed, e)
        return _error("TOOL_EXECUTION_ERROR", str(e))


def _import_path(tool_name: str) -> str:
    from mcp_server.core.registry import TOOL_REGISTRY
    return TOOL_REGISTRY[tool_name]


def _error(code: str, message: str) -> dict:
    return {
        "success": False,
        "data": None,
        "error": {
            "code": code,
            "message": message
        },
        "meta": {}
    }