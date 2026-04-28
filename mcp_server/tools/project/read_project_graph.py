"""
MCP Tool: read_project_graph

Lightweight project scanner with optional full dependency graph.

Args:
    path (str): Project root directory.
    focus (list[str]): Optional list of subdirectory names to restrict scan.
    depth (int): Max directory depth (default 2).
    include_dependencies (bool): When true, build and return the full
        cross-reference dependency graph (nodes + edges). Default false.

Returns:
    {
        "graph": [...],          # file → symbols map (always)
        "dependency_graph": {    # only when include_dependencies=true
            "nodes": [...],
            "edges": [...],
            "stats": {...}
        }
    }
"""

import logging
import os

from analysis.ast.parser import ProjectSymbolParser
from analysis.graph.dependency_graph import DependencyGraph

logger = logging.getLogger("mcp.tool.read_project_graph")

EXCLUDED_DIRS = {"venv", ".venv", ".git", "__pycache__", "node_modules",
                 ".tox", ".mypy_cache"}

# Module-level singleton (graph is cached inside DependencyGraph)
_dep_graph = DependencyGraph()


async def run(args: dict) -> dict:
    """
    Lightweight scan of the project structure.
    Returns file paths and top-level symbols (classes/functions)
    without internal details to minimize context usage.

    When include_dependencies=true, also returns the full cross-reference
    dependency graph with CALLS, USES, and INHERITS edges.
    """
    directory = args.get("path") or args.get("directory", ".")
    focus = args.get("focus", [])
    max_depth = args.get("depth", 2)
    include_dependencies = args.get("include_dependencies", False)

    if not os.path.exists(directory):
        return _error("INVALID_DIRECTORY", f"Directory not found: {directory}")

    try:
        parser = ProjectSymbolParser()
        project_graph = []
        root_depth = directory.rstrip(os.sep).count(os.sep)

        for dirpath, dirnames, files in os.walk(directory):
            dirnames[:] = [d for d in dirnames if d not in EXCLUDED_DIRS]

            current_depth = dirpath.rstrip(os.sep).count(os.sep) - root_depth
            if current_depth > max_depth:
                dirnames.clear()
                continue
            elif current_depth == max_depth:
                dirnames.clear()

            if focus:
                dir_basename = os.path.basename(dirpath)
                if dirpath != directory and dir_basename not in focus:
                    continue

            for file in files:
                if not file.endswith(".py"):
                    continue
                filepath = os.path.join(dirpath, file)
                symbols = parser.parse_file(filepath)

                if symbols:
                    class_symbols = [
                        {
                            "name": sym["name"],
                            "type_hint": sym["type_hint"],
                            "chunk_type": sym.get("chunk_type", sym["type_hint"]),
                            "decorators": sym.get("decorators", []),
                            "docstring": sym.get("docstring"),
                        }
                        for sym in symbols
                        if sym["type"] == "class"
                    ]
                    func_symbols = [
                        {
                            "name": sym["name"],
                            "type_hint": sym["type_hint"],
                            "chunk_type": sym.get("chunk_type", sym["type_hint"]),
                            "decorators": sym.get("decorators", []),
                            "docstring": sym.get("docstring"),
                        }
                        for sym in symbols
                        if sym["type"] == "function"
                    ]

                    entry = {"file": os.path.relpath(filepath, directory)}
                    if class_symbols:
                        entry["classes"] = class_symbols
                    if func_symbols:
                        entry["functions"] = func_symbols

                    project_graph.append(entry)

        # ------------------------------------------------------------------
        # Optional: full dependency graph
        # ------------------------------------------------------------------
        dep_graph_data = None
        if include_dependencies:
            logger.info("Building dependency graph for %s ...", directory)
            dep_graph_data = _dep_graph.build(directory)

        response_data: dict = {"graph": project_graph}
        if dep_graph_data is not None:
            response_data["dependency_graph"] = dep_graph_data

        return {
            "success": True,
            "data": response_data,
            "error": None,
            "meta": {
                "root": directory,
                "files_scanned": len(project_graph),
                "focus": focus or "all",
                "depth": max_depth,
                "include_dependencies": include_dependencies,
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