import os
import logging

from analysis.ast.parser import ProjectSymbolParser

logger = logging.getLogger("mcp.tool.read_project_graph")

# Directories to always exclude from scanning
EXCLUDED_DIRS = {"venv", ".venv", ".git", "__pycache__", "node_modules", ".tox", ".mypy_cache"}


async def run(args: dict) -> dict:
    """
    Lightweight scan of the project structure.
    Returns file paths and top-level symbols (classes/functions)
    without internal details to minimize context usage.
    """
    directory = args.get("path") or args.get("directory", ".")
    focus = args.get("focus", [])  # e.g. ["schemas", "agents", "tools"]
    max_depth = args.get("depth", 2)

    if not os.path.exists(directory):
        return _error("INVALID_DIRECTORY", f"Directory not found: {directory}")

    try:
        parser = ProjectSymbolParser()
        project_graph = []
        root_depth = directory.rstrip(os.sep).count(os.sep)

        for dirpath, dirnames, files in os.walk(directory):
            # Prune excluded dirs in-place so os.walk skips them
            dirnames[:] = [d for d in dirnames if d not in EXCLUDED_DIRS]

            # Enforce depth limit
            current_depth = dirpath.rstrip(os.sep).count(os.sep) - root_depth
            if current_depth >= max_depth:
                dirnames.clear()
                continue

            # If focus filters are set, only include matching directory names
            if focus:
                dir_basename = os.path.basename(dirpath)
                # Allow the root directory itself, and any dir matching focus
                if dirpath != directory and dir_basename not in focus:
                    continue

            for file in files:
                if file.endswith(".py"):
                    filepath = os.path.join(dirpath, file)
                    symbols = parser.parse_file(filepath)

                    if symbols:
                        class_symbols = [
                            {"name": sym["name"], "type_hint": sym["type_hint"]}
                            for sym in symbols
                            if sym["type"] == "class"
                        ]
                        func_symbols = [
                            {"name": sym["name"], "type_hint": sym["type_hint"]}
                            for sym in symbols
                            if sym["type"] == "function"
                        ]

                        entry = {
                            "file": os.path.relpath(filepath, directory),
                        }
                        if class_symbols:
                            entry["classes"] = class_symbols
                        if func_symbols:
                            entry["functions"] = func_symbols

                        project_graph.append(entry)

        return {
            "success": True,
            "data": {
                "graph": project_graph,
            },
            "error": None,
            "meta": {
                "root": directory,
                "files_scanned": len(project_graph),
                "focus": focus or "all",
                "depth": max_depth,
            },
        }
    except Exception as e:
        logger.exception("Error in read_project_graph")
        return _error("AST_PARSE_ERROR", str(e))


def _error(code: str, message: str) -> dict:
    return {
        "success": False,
        "data": None,
        "error": {"code": code, "message": message},
        "meta": {},
    }