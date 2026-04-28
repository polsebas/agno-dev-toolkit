"""
Dependency Graph Engine — Cursor-style cross-reference index.

Builds a directed graph of code relationships from a project directory:

  Node A (AgentClass)  --CALLS-->     Node B (tool_function)
  Node A (AgentClass)  --USES-->      Node C (PydanticModel)
  Node A (AgentClass)  --INHERITS-->  Node D (BaseAgent)

The graph is computed in-memory from SemanticChunks and returned as a
plain dict suitable for JSON serialisation in MCP responses.

Usage:
    from analysis.graph.dependency_graph import DependencyGraph
    graph = DependencyGraph()
    result = graph.build("/path/to/user/project")
    # result = {"nodes": [...], "edges": [...]}
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Dict, List, Set

from analysis.ast.semantic_chunker import SemanticChunk, SemanticChunker

logger = logging.getLogger("analysis.graph.dependency_graph")

EXCLUDED_DIRS = {"venv", ".venv", ".git", "__pycache__", "node_modules",
                 ".tox", ".mypy_cache", "dist", "build", ".pytest_cache"}

# Edge relationship types
EDGE_CALLS = "CALLS"
EDGE_USES = "USES"
EDGE_INHERITS = "INHERITS"


class DependencyGraph:
    """
    Builds and queries a cross-reference dependency graph for a Python project.

    The graph is computed lazily on first call to .build() and cached by root path.
    """

    def __init__(self) -> None:
        self._chunker = SemanticChunker()
        self._cache: Dict[str, dict] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build(self, project_root: str, max_depth: int = 10,
              invalidate_cache: bool = False) -> dict:
        """
        Walk the project, extract all SemanticChunks, and build the graph.

        Returns:
            {
                "nodes": [NodeDict, ...],
                "edges": [EdgeDict, ...],
                "stats": {"files": int, "nodes": int, "edges": int}
            }
        """
        project_root = str(Path(project_root).resolve())

        if not invalidate_cache and project_root in self._cache:
            logger.debug("DependencyGraph: cache hit for %s", project_root)
            return self._cache[project_root]

        all_chunks = self._scan_project(project_root, max_depth)
        result = self._build_graph(all_chunks, project_root)
        self._cache[project_root] = result
        return result

    def get_callers(self, symbol_name: str, project_root: str) -> List[str]:
        """Return list of symbol names that call the given symbol."""
        graph = self.build(project_root)
        return [
            e["from"] for e in graph["edges"]
            if e["to"] == symbol_name and e["type"] == EDGE_CALLS
        ]

    def get_callees(self, symbol_name: str, project_root: str) -> List[str]:
        """Return list of symbol names that this symbol calls."""
        graph = self.build(project_root)
        return [
            e["to"] for e in graph["edges"]
            if e["from"] == symbol_name and e["type"] == EDGE_CALLS
        ]

    def get_impact(self, symbol_name: str, project_root: str) -> List[str]:
        """
        Return all symbols that would be *affected* if the given symbol changes.
        Performs a BFS over incoming CALLS/USES edges.
        """
        graph = self.build(project_root)
        # Build adjacency for reverse traversal
        reverse: Dict[str, Set[str]] = {}
        for edge in graph["edges"]:
            reverse.setdefault(edge["to"], set()).add(edge["from"])

        visited: Set[str] = set()
        queue = [symbol_name]
        while queue:
            current = queue.pop()
            for caller in reverse.get(current, []):
                if caller not in visited:
                    visited.add(caller)
                    queue.append(caller)

        visited.discard(symbol_name)
        return sorted(visited)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _scan_project(self, root: str, max_depth: int) -> List[SemanticChunk]:
        """Walk the project and return all semantic chunks."""
        chunks: List[SemanticChunk] = []
        root_depth = root.rstrip(os.sep).count(os.sep)

        for dirpath, dirnames, files in os.walk(root):
            # Prune excluded dirs in-place
            dirnames[:] = [d for d in dirnames if d not in EXCLUDED_DIRS]

            current_depth = dirpath.rstrip(os.sep).count(os.sep) - root_depth
            if current_depth > max_depth:
                dirnames.clear()
                continue

            for fname in files:
                if not fname.endswith(".py"):
                    continue
                fpath = os.path.join(dirpath, fname)
                try:
                    file_chunks = self._chunker.chunk_file(fpath)
                    # Store relative paths for cleaner output
                    rel = os.path.relpath(fpath, root)
                    for c in file_chunks:
                        c.file_path = rel
                    chunks.extend(file_chunks)
                except Exception as e:
                    logger.debug("Skipping %s: %s", fpath, e)

        logger.debug("DependencyGraph: scanned %d chunks from %s", len(chunks), root)
        return chunks

    def _build_graph(self, chunks: List[SemanticChunk], project_root: str) -> dict:
        """Build node and edge lists from chunks."""
        # Index all known symbol names for reference resolution
        symbol_index: Dict[str, SemanticChunk] = {
            c.symbol_name: c for c in chunks if c.symbol_name != "module_docstring"
        }
        known_names = set(symbol_index.keys())

        nodes: List[dict] = []
        edges: List[dict] = []
        seen_edges: Set[tuple] = set()

        def _add_edge(frm: str, to: str, etype: str):
            key = (frm, to, etype)
            if key not in seen_edges and frm != to:
                seen_edges.add(key)
                edges.append({"from": frm, "to": to, "type": etype})

        # Cache pydantic models to avoid redundant O(N) extraction in the loop
        pydantic_models = {
            name for name, c in symbol_index.items()
            if c.chunk_type == "pydantic_model"
        }

        for chunk in chunks:
            if chunk.symbol_name == "module_docstring":
                continue

            # Build node
            nodes.append({
                "id": chunk.symbol_name,
                "chunk_type": chunk.chunk_type,
                "file_path": chunk.file_path,
                "line_start": chunk.line_start,
                "line_end": chunk.line_end,
                "decorators": chunk.decorators,
                "docstring": chunk.docstring,
            })

            # INHERITS edges (class bases)
            for base in chunk.bases:
                if base in known_names:
                    _add_edge(chunk.symbol_name, base, EDGE_INHERITS)

            # CALLS edges (function call references in body)
            for callee in chunk.calls:
                if callee in known_names:
                    _add_edge(chunk.symbol_name, callee, EDGE_CALLS)

            # USES edges — detect Pydantic model references via type annotations
            for model_name in pydantic_models:
                if model_name != chunk.symbol_name and model_name in chunk.text:
                    _add_edge(chunk.symbol_name, model_name, EDGE_USES)

        return {
            "nodes": nodes,
            "edges": edges,
            "stats": {
                "files": len({c.file_path for c in chunks}),
                "nodes": len(nodes),
                "edges": len(edges),
            },
        }
