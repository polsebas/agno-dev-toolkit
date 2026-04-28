"""
Semantic chunker powered by tree-sitter.

Replaces the line-based chunker.py for Python source files. Extracts
logical code units (classes, functions, @tool decorators, Pydantic models)
as typed SemanticChunk objects with stable content hashes.

Usage (RAG ingestion):
    from analysis.ast.semantic_chunker import SemanticChunker
    chunks = SemanticChunker().chunk_file(path)

Usage (live project scan):
    chunks = SemanticChunker().chunk_source(source_code, file_path="agents/my_agent.py")
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger("analysis.ast.semantic_chunker")

# ---------------------------------------------------------------------------
# Grammar bootstrap — cached at module level (one-time cost)
# ---------------------------------------------------------------------------
try:
    from tree_sitter import Language, Parser
    import tree_sitter_python as tspython

    _PY_LANGUAGE = Language(tspython.language())
    _PARSER = Parser(_PY_LANGUAGE)
    _TREESITTER_AVAILABLE = True
except Exception as _ts_err:
    logger.warning("tree-sitter unavailable (%s), falling back to ast module", _ts_err)
    _TREESITTER_AVAILABLE = False
    _PY_LANGUAGE = None
    _PARSER = None


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

CHUNK_TYPES = (
    "agno_tool",        # function decorated with @tool
    "pydantic_model",   # class inheriting BaseModel
    "agent_class",      # class inheriting Agent / team
    "plain_class",      # any other top-level class
    "module_function",  # top-level function (not @tool)
    "module_docstring", # module-level docstring
)


@dataclass
class SemanticChunk:
    """A single logical code unit extracted from a Python file."""

    # Core content
    text: str                   # Exact source text of the symbol
    symbol_name: str            # Class/function name (or "module_docstring")
    chunk_type: str             # One of CHUNK_TYPES

    # Location
    file_path: str              # Relative or absolute path to source file
    line_start: int             # 1-indexed
    line_end: int               # 1-indexed, inclusive

    # Derived
    content_hash: str = field(init=False)  # SHA-256 of text
    decorators: List[str] = field(default_factory=list)
    docstring: Optional[str] = None
    bases: List[str] = field(default_factory=list)  # For classes
    calls: List[str] = field(default_factory=list)  # Identifiers called in body

    def __post_init__(self) -> None:
        self.content_hash = hashlib.sha256(self.text.encode()).hexdigest()

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "symbol_name": self.symbol_name,
            "chunk_type": self.chunk_type,
            "file_path": self.file_path,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "content_hash": self.content_hash,
            "decorators": self.decorators,
            "docstring": self.docstring,
            "bases": self.bases,
            "calls": self.calls,
        }


# ---------------------------------------------------------------------------
# Tree-sitter query patterns (s-expressions)
# ---------------------------------------------------------------------------

# Match top-level class definitions
_CLASS_QUERY_SRC = """
(module
  (class_definition
    name: (identifier) @class.name
    bases: (argument_list)? @class.bases
    body: (block
      (expression_statement
        (string) @class.docstring)?))
  @class.def)
"""

# Match top-level function / async function definitions
_FUNC_QUERY_SRC = """
(module
  [
    (function_definition
      name: (identifier) @func.name
      body: (block
        (expression_statement
          (string) @func.docstring)?)
      @func.def)
    (decorated_definition
      (decorator)+ @func.decorator
      definition: (function_definition
        name: (identifier) @func.name
        body: (block
          (expression_statement
            (string) @func.docstring)?))
      @func.def)
    (decorated_definition
      (decorator)+ @func.decorator
      definition: (async_function_definition
        name: (identifier) @func.name
        body: (block
          (expression_statement
            (string) @func.docstring)?))
      @func.def)
    (async_function_definition
      name: (identifier) @func.name
      body: (block
        (expression_statement
          (string) @func.docstring)?)
      @func.def)
  ])
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _node_text(node, source_bytes: bytes) -> str:
    return source_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="replace")


def _extract_decorators(decorated_node, source_bytes: bytes) -> List[str]:
    """Extract decorator names from a decorated_definition node."""
    decorators = []
    for child in decorated_node.children:
        if child.type == "decorator":
            text = _node_text(child, source_bytes).strip().lstrip("@")
            # Normalise: @tool(...) → tool
            name = text.split("(")[0].split(".")[-1]
            decorators.append(name)
    return decorators


def _extract_calls(func_body_node, source_bytes: bytes) -> List[str]:
    """Walk a function body and collect all identifiers used as calls."""
    calls: List[str] = []

    def _walk(node):
        if node.type == "call":
            func_child = node.child_by_field_name("function")
            if func_child:
                if func_child.type == "identifier":
                    calls.append(_node_text(func_child, source_bytes))
                elif func_child.type == "attribute":
                    attr = func_child.child_by_field_name("attribute")
                    if attr:
                        calls.append(_node_text(attr, source_bytes))
        for child in node.children:
            _walk(child)

    _walk(func_body_node)
    return list(dict.fromkeys(calls))  # dedupe, preserve order


def _extract_bases(class_node, source_bytes: bytes) -> List[str]:
    """Extract base class names from a class_definition node."""
    bases: List[str] = []
    bases_node = class_node.child_by_field_name("superclasses")
    if bases_node is None:
        # try argument_list child
        for child in class_node.children:
            if child.type == "argument_list":
                bases_node = child
                break
    if bases_node:
        for child in bases_node.children:
            if child.type in ("identifier", "attribute"):
                text = _node_text(child, source_bytes)
                bases.append(text.split(".")[-1])
    return bases


def _classify_class(name: str, bases: List[str]) -> str:
    base_set = {b.lower() for b in bases}
    if "basemodel" in base_set or "model" in base_set:
        return "pydantic_model"
    if any(b in base_set for b in ("agent", "team", "agentteam")):
        return "agent_class"
    if "agent" in name.lower() or "team" in name.lower():
        return "agent_class"
    return "plain_class"


def _classify_function(decorators: List[str]) -> str:
    dec_set = {d.lower() for d in decorators}
    if "tool" in dec_set:
        return "agno_tool"
    return "module_function"


def _extract_docstring_from_node(node, source_bytes: bytes) -> Optional[str]:
    """Return the docstring text if the first body statement is a string literal."""
    body = node.child_by_field_name("body")
    if body is None:
        return None
    for child in body.children:
        if child.type == "expression_statement":
            for sub in child.children:
                if sub.type == "string":
                    raw = _node_text(sub, source_bytes).strip()
                    # Strip quotes
                    for q in ('"""', "'''", '"', "'"):
                        if raw.startswith(q) and raw.endswith(q) and len(raw) > 2 * len(q):
                            return raw[len(q):-len(q)].strip()
                    return raw
        break
    return None


# ---------------------------------------------------------------------------
# Core chunker
# ---------------------------------------------------------------------------

class SemanticChunker:
    """
    Extracts SemanticChunk units from Python source using tree-sitter.

    Falls back to the stdlib `ast` module when tree-sitter is unavailable.
    """

    def chunk_file(self, path: str | Path) -> List[SemanticChunk]:
        """Parse a file on disk and return semantic chunks."""
        path = Path(path)
        try:
            source = path.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            logger.warning("Cannot read %s: %s", path, e)
            return []
        return self.chunk_source(source, file_path=str(path))

    def chunk_source(self, source: str, file_path: str = "<string>") -> List[SemanticChunk]:
        """Parse source code string and return semantic chunks."""
        if _TREESITTER_AVAILABLE:
            return self._chunk_with_treesitter(source, file_path)
        return self._chunk_with_ast(source, file_path)

    # ------------------------------------------------------------------
    # tree-sitter backend
    # ------------------------------------------------------------------

    def _chunk_with_treesitter(self, source: str, file_path: str) -> List[SemanticChunk]:
        source_bytes = source.encode("utf-8")
        tree = _PARSER.parse(source_bytes)
        chunks: List[SemanticChunk] = []

        # Module docstring (first statement is a string)
        for child in tree.root_node.children:
            if child.type == "expression_statement":
                for sub in child.children:
                    if sub.type == "string":
                        text = _node_text(sub, source_bytes).strip()
                        chunks.append(SemanticChunk(
                            text=text,
                            symbol_name="module_docstring",
                            chunk_type="module_docstring",
                            file_path=file_path,
                            line_start=sub.start_point[0] + 1,
                            line_end=sub.end_point[0] + 1,
                        ))
                break

        # Top-level class and function definitions
        for node in tree.root_node.children:
            if node.type == "class_definition":
                chunk = self._process_class_node(node, source_bytes, file_path)
                if chunk:
                    chunks.append(chunk)

            elif node.type in ("function_definition", "async_function_definition"):
                chunk = self._process_func_node(node, source_bytes, file_path, decorators=[])
                if chunk:
                    chunks.append(chunk)

            elif node.type == "decorated_definition":
                decorators = _extract_decorators(node, source_bytes)
                inner = None
                for child in node.children:
                    if child.type in ("function_definition", "async_function_definition"):
                        inner = child
                        break
                    elif child.type == "class_definition":
                        inner = child
                        break
                if inner is None:
                    continue
                if inner.type == "class_definition":
                    chunk = self._process_class_node(inner, source_bytes, file_path,
                                                     extra_decorators=decorators,
                                                     outer_node=node)
                else:
                    chunk = self._process_func_node(inner, source_bytes, file_path,
                                                    decorators=decorators,
                                                    outer_node=node)
                if chunk:
                    chunks.append(chunk)

        return chunks

    def _process_class_node(self, node, source_bytes: bytes, file_path: str,
                             extra_decorators: List[str] = None,
                             outer_node=None) -> Optional[SemanticChunk]:
        name_node = node.child_by_field_name("name")
        if not name_node:
            return None
        name = _node_text(name_node, source_bytes)
        bases = _extract_bases(node, source_bytes)
        chunk_type = _classify_class(name, bases)
        docstring = _extract_docstring_from_node(node, source_bytes)

        effective_node = outer_node if outer_node else node
        text = _node_text(effective_node, source_bytes)

        return SemanticChunk(
            text=text,
            symbol_name=name,
            chunk_type=chunk_type,
            file_path=file_path,
            line_start=effective_node.start_point[0] + 1,
            line_end=effective_node.end_point[0] + 1,
            decorators=extra_decorators or [],
            docstring=docstring,
            bases=bases,
            calls=[],
        )

    def _process_func_node(self, node, source_bytes: bytes, file_path: str,
                            decorators: List[str],
                            outer_node=None) -> Optional[SemanticChunk]:
        name_node = node.child_by_field_name("name")
        if not name_node:
            return None
        name = _node_text(name_node, source_bytes)
        chunk_type = _classify_function(decorators)
        docstring = _extract_docstring_from_node(node, source_bytes)

        body = node.child_by_field_name("body")
        calls = _extract_calls(body, source_bytes) if body else []

        effective_node = outer_node if outer_node else node
        text = _node_text(effective_node, source_bytes)

        return SemanticChunk(
            text=text,
            symbol_name=name,
            chunk_type=chunk_type,
            file_path=file_path,
            line_start=effective_node.start_point[0] + 1,
            line_end=effective_node.end_point[0] + 1,
            decorators=decorators,
            docstring=docstring,
            bases=[],
            calls=calls,
        )

    # ------------------------------------------------------------------
    # stdlib ast fallback
    # ------------------------------------------------------------------

    def _chunk_with_ast(self, source: str, file_path: str) -> List[SemanticChunk]:
        """Fallback using stdlib ast — less accurate but always available."""
        import ast as _ast

        try:
            tree = _ast.parse(source)
        except SyntaxError:
            return []

        lines = source.splitlines()
        chunks: List[SemanticChunk] = []

        for node in tree.body:
            if isinstance(node, _ast.ClassDef):
                bases = [
                    (b.id if isinstance(b, _ast.Name) else b.attr)
                    for b in node.bases
                    if isinstance(b, (_ast.Name, _ast.Attribute))
                ]
                chunk_type = _classify_class(node.name, bases)
                text = "\n".join(lines[node.lineno - 1: node.end_lineno])
                doc = _ast.get_docstring(node)
                chunks.append(SemanticChunk(
                    text=text, symbol_name=node.name, chunk_type=chunk_type,
                    file_path=file_path, line_start=node.lineno,
                    line_end=node.end_lineno or node.lineno,
                    bases=bases, docstring=doc,
                ))

            elif isinstance(node, (_ast.FunctionDef, _ast.AsyncFunctionDef)):
                dec_names = []
                for d in node.decorator_list:
                    if isinstance(d, _ast.Name):
                        dec_names.append(d.id)
                    elif isinstance(d, _ast.Attribute):
                        dec_names.append(d.attr)
                    elif isinstance(d, _ast.Call):
                        f = d.func
                        dec_names.append(f.id if isinstance(f, _ast.Name) else
                                         (f.attr if isinstance(f, _ast.Attribute) else ""))
                chunk_type = _classify_function(dec_names)
                text = "\n".join(lines[node.lineno - 1: node.end_lineno])
                doc = _ast.get_docstring(node)
                chunks.append(SemanticChunk(
                    text=text, symbol_name=node.name, chunk_type=chunk_type,
                    file_path=file_path, line_start=node.lineno,
                    line_end=node.end_lineno or node.lineno,
                    decorators=dec_names, docstring=doc,
                ))

        return chunks
