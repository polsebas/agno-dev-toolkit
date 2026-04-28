"""
MCP Tool: query_local_architecture

Deep inspection of a specific local symbol (e.g. a Pydantic model).

New in this version:
- chunk_type — semantic classification (agno_tool, pydantic_model, agent_class, …)
- callers     — which symbols call this one (from dependency graph)
- callees     — which symbols this one calls
- impact      — transitive set of symbols that would break if this changes
- decorators  — decorator list from tree-sitter extraction
"""

import ast
import logging

from analysis.ast.parser import ProjectSymbolParser
from analysis.graph.dependency_graph import DependencyGraph

logger = logging.getLogger("mcp.tool.query_local_architecture")

_dep_graph = DependencyGraph()


async def run(args: dict) -> dict:
    """
    Deep inspection of a specific local symbol (e.g. a Pydantic model).
    Returns exact code definition, semantic classification, and dependency context.
    """
    identifier = args.get("identifier")
    directory = args.get("path") or args.get("directory", ".")
    include_definition = args.get("include_definition", True)
    compression = args.get("compression", "none")

    if not identifier:
        return _error("INVALID_INPUT", "Provide 'identifier' to search for.")

    try:
        target_name = identifier.split(".")[-1]
        
        # 1. Usar el grafo (cacheado) para localizar el archivo al instante
        graph = _dep_graph.build(directory)
        filepath = None
        for node in graph.get("nodes", []):
            if node["id"] == target_name:
                filepath = node["file_path"]
                break
                
        symbol_info = None
        if filepath:
            # Resolver path absoluto si es relativo
            import os
            full_path = os.path.join(directory, filepath) if not os.path.isabs(filepath) else filepath
            
            parser = ProjectSymbolParser()
            symbols_in_file = parser.parse_file(full_path)
            for sym in symbols_in_file:
                if sym["name"] == target_name:
                    sym["filepath"] = full_path
                    symbol_info = sym
                    break

        if not symbol_info:
            return _error(
                "SYMBOL_NOT_FOUND",
                f"Could not find symbol: {identifier} in directory {directory}",
            )

        # Apply compression to the source definition
        source = symbol_info.get("source", "")
        if include_definition and source:
            source = _compress(source, compression)
        elif not include_definition:
            source = None

        # ------------------------------------------------------------------
        # Dependency context (callers, callees, impact analysis)
        # ------------------------------------------------------------------
        callers = []
        callees = []
        impact = []
        try:
            callers = _dep_graph.get_callers(identifier.split(".")[-1], directory)
            callees = _dep_graph.get_callees(identifier.split(".")[-1], directory)
            impact = _dep_graph.get_impact(identifier.split(".")[-1], directory)
        except Exception as e:
            logger.debug("Dependency graph unavailable: %s", e)

        return {
            "success": True,
            "data": {
                "identifier": identifier,
                "filepath": symbol_info.get("filepath"),
                "type": symbol_info.get("type"),

                # Semantic classification (new)
                "chunk_type": symbol_info.get("chunk_type", symbol_info.get("type_hint")),
                "decorators": symbol_info.get("decorators", []),
                "docstring": symbol_info.get("docstring"),
                "line_start": symbol_info.get("line_start"),
                "line_end": symbol_info.get("line_end"),
                "content_hash": symbol_info.get("content_hash"),

                # Code definition
                "definition": source,

                # Legacy field (base classes)
                "dependencies": symbol_info.get("bases", []),

                # Cross-reference graph (new)
                "callers": callers,
                "callees": callees,
                "impact": impact,
            },
            "error": None,
            "meta": {
                "compression": compression,
            },
        }
    except Exception as e:
        logger.exception("Error in query_local_architecture")
        return _error("AST_PARSE_ERROR", str(e))


def _compress(source: str, mode: str) -> str:
    """Apply compression to source code."""
    if mode == "truncated":
        lines = source.split("\n")
        if len(lines) > 20:
            return "\n".join(lines[:20]) + "\n# ... truncated ..."
        return source
    elif mode == "summarized":
        try:
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                    sig_lines = [source.split("\n")[0]]
                    if (node.body
                            and isinstance(node.body[0], ast.Expr)
                            and isinstance(node.body[0].value, ast.Constant)):
                        doc = ast.get_source_segment(source, node.body[0])
                        if doc:
                            sig_lines.append(f"    {doc}")
                    sig_lines.append("    ...")
                    return "\n".join(sig_lines)
        except Exception:
            pass
        return source.split("\n")[0] + "\n    ..."
    return source


def _error(code: str, message: str) -> dict:
    return {
        "success": False,
        "data": None,
        "error": {"code": code, "message": message},
        "meta": {},
    }
