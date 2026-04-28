"""
Project symbol parser — enhanced with tree-sitter and SemanticChunker.

Provides the ProjectSymbolParser used by the MCP tools
(read_project_graph, query_local_architecture). Now backed by the
SemanticChunker for richer extraction: decorators, docstrings, call-graph.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List

from analysis.ast.semantic_chunker import SemanticChunker, SemanticChunk

_EXCLUDED = {"venv", ".venv", ".git", "__pycache__", "node_modules",
             ".tox", ".mypy_cache"}


def _chunk_to_symbol(chunk: SemanticChunk) -> Dict[str, Any]:
    """Convert a SemanticChunk to the legacy symbol dict format (backward compat)."""
    return {
        "name": chunk.symbol_name,
        "type": "class" if "class" in chunk.chunk_type or "model" in chunk.chunk_type else "function",
        "type_hint": chunk.chunk_type,
        "bases": chunk.bases,
        "source": chunk.text,
        # New fields
        "chunk_type": chunk.chunk_type,
        "decorators": chunk.decorators,
        "docstring": chunk.docstring,
        "line_start": chunk.line_start,
        "line_end": chunk.line_end,
        "content_hash": chunk.content_hash,
        "calls": chunk.calls,
    }


class ProjectSymbolParser:
    """
    Parses Python source files and extracts structural symbols.

    Backed by SemanticChunker (tree-sitter) for accurate extraction of:
    - Pydantic models (BaseModel subclasses)
    - @tool decorated functions (agno_tool)
    - Agent classes (agent_class)
    - Plain classes and module-level functions
    """

    def __init__(self) -> None:
        self._chunker = SemanticChunker()

    def parse_file(self, filepath: str) -> List[Dict[str, Any]]:
        """Parse a single file and return its top-level symbols."""
        if not os.path.exists(filepath):
            return []
        try:
            chunks = self._chunker.chunk_file(filepath)
            return [
                _chunk_to_symbol(c) for c in chunks
                if c.symbol_name != "module_docstring"
            ]
        except Exception:
            return []

    def find_symbol(self, project_root: str, identifier: str) -> Dict[str, Any]:
        """
        Locate a symbol by name (e.g. 'UserSchema' or 'schemas.user.UserSchema').
        Returns enriched symbol dict including calls, decorators, chunk_type.
        """
        target_name = identifier.split(".")[-1]

        for root, dirnames, files in os.walk(project_root):
            dirnames[:] = [d for d in dirnames if d not in _EXCLUDED]
            for fname in files:
                if not fname.endswith(".py"):
                    continue
                fpath = os.path.join(root, fname)
                try:
                    chunks = self._chunker.chunk_file(fpath)
                    for chunk in chunks:
                        if chunk.symbol_name == target_name:
                            sym = _chunk_to_symbol(chunk)
                            sym["filepath"] = fpath
                            return sym
                except Exception:
                    continue
        return {}
