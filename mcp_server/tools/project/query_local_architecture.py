import ast
import logging

from analysis.ast.parser import ProjectSymbolParser

logger = logging.getLogger("mcp.tool.query_local_architecture")


async def run(args: dict) -> dict:
    """
    Deep inspection of a specific local symbol (e.g. a Pydantic model).
    Returns exact code definition and dependencies.
    """
    identifier = args.get("identifier")
    directory = args.get("directory", ".")
    include_definition = args.get("include_definition", True)
    compression = args.get("compression", "none")  # none | truncated | summarized

    if not identifier:
        return _error("INVALID_INPUT", "Provide 'identifier' to search for.")

    try:
        parser = ProjectSymbolParser()
        symbol_info = parser.find_symbol(directory, identifier)

        if not symbol_info:
            return _error(
                "SYMBOL_NOT_FOUND",
                f"Could not find symbol: {identifier}",
            )

        # Apply compression to the source definition
        source = symbol_info.get("source", "")
        if include_definition and source:
            source = _compress(source, compression)
        elif not include_definition:
            source = None

        return {
            "success": True,
            "data": {
                "identifier": identifier,
                "filepath": symbol_info.get("filepath"),
                "type": symbol_info.get("type"),
                "type_hint": symbol_info.get("type_hint"),
                "definition": source,
                "dependencies": symbol_info.get("bases", []),
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
        # Extract just the signature (first line of class/function def)
        try:
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                    sig_lines = []
                    sig_lines.append(source.split("\n")[0])
                    # Include docstring if present
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
        # Fallback: first line
        return source.split("\n")[0] + "\n    ..."
    # mode == "none"
    return source


def _error(code: str, message: str) -> dict:
    return {
        "success": False,
        "data": None,
        "error": {"code": code, "message": message},
        "meta": {},
    }
