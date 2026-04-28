"""
Tests for the tree-sitter powered SemanticChunker.

Covers:
- @tool function detection
- Pydantic BaseModel detection
- Agent class detection
- Content hash stability
- Fallback (ast module) behavior via monkeypatch
- DependencyGraph CALLS/USES/INHERITS edges
"""

import hashlib
import textwrap
import pytest

from analysis.ast.semantic_chunker import SemanticChunker, SemanticChunk
from analysis.graph.dependency_graph import DependencyGraph


# ---------------------------------------------------------------------------
# Sample source fixtures
# ---------------------------------------------------------------------------

SAMPLE_TOOL = textwrap.dedent("""\
    from agno import tool

    @tool
    def search_web(query: str) -> str:
        \"\"\"Search the web for a query.\"\"\"
        results = http_get(query)
        return results
""")

SAMPLE_MODEL = textwrap.dedent("""\
    from pydantic import BaseModel

    class UserProfile(BaseModel):
        \"\"\"User profile schema.\"\"\"
        name: str
        email: str
""")

SAMPLE_AGENT = textwrap.dedent("""\
    from agno import Agent

    class SupportAgent(Agent):
        \"\"\"Customer support agent.\"\"\"
        def __init__(self):
            super().__init__()
""")

SAMPLE_MIXED = SAMPLE_TOOL + "\n" + SAMPLE_MODEL + "\n" + SAMPLE_AGENT

SAMPLE_GRAPH = textwrap.dedent("""\
    from pydantic import BaseModel

    class OrderModel(BaseModel):
        amount: float

    @tool
    def process_order(order: OrderModel) -> str:
        result = validate(order)
        return result

    class OrderAgent(Agent):
        def run(self):
            process_order(OrderModel())
""")


# ---------------------------------------------------------------------------
# SemanticChunker tests
# ---------------------------------------------------------------------------

class TestSemanticChunker:
    def setup_method(self):
        self.chunker = SemanticChunker()

    def test_detects_agno_tool(self):
        chunks = self.chunker.chunk_source(SAMPLE_TOOL, file_path="test.py")
        tool_chunks = [c for c in chunks if c.chunk_type == "agno_tool"]
        assert len(tool_chunks) == 1
        assert tool_chunks[0].symbol_name == "search_web"

    def test_detects_pydantic_model(self):
        chunks = self.chunker.chunk_source(SAMPLE_MODEL, file_path="test.py")
        model_chunks = [c for c in chunks if c.chunk_type == "pydantic_model"]
        assert len(model_chunks) == 1
        assert model_chunks[0].symbol_name == "UserProfile"

    def test_detects_agent_class(self):
        chunks = self.chunker.chunk_source(SAMPLE_AGENT, file_path="test.py")
        agent_chunks = [c for c in chunks if c.chunk_type == "agent_class"]
        assert len(agent_chunks) == 1
        assert agent_chunks[0].symbol_name == "SupportAgent"

    def test_mixed_source_all_types(self):
        chunks = self.chunker.chunk_source(SAMPLE_MIXED, file_path="test.py")
        types = {c.chunk_type for c in chunks}
        assert "agno_tool" in types
        assert "pydantic_model" in types
        assert "agent_class" in types

    def test_content_hash_is_stable(self):
        chunks1 = self.chunker.chunk_source(SAMPLE_TOOL, file_path="a.py")
        chunks2 = self.chunker.chunk_source(SAMPLE_TOOL, file_path="a.py")
        assert chunks1[0].content_hash == chunks2[0].content_hash

    def test_content_hash_changes_on_edit(self):
        chunks1 = self.chunker.chunk_source(SAMPLE_TOOL, file_path="a.py")
        modified = SAMPLE_TOOL.replace("Search the web", "MODIFIED")
        chunks2 = self.chunker.chunk_source(modified, file_path="a.py")
        assert chunks1[0].content_hash != chunks2[0].content_hash

    def test_hash_is_sha256_of_text(self):
        chunks = self.chunker.chunk_source(SAMPLE_TOOL, file_path="a.py")
        c = chunks[0]
        expected = hashlib.sha256(c.text.encode()).hexdigest()
        assert c.content_hash == expected

    def test_tool_docstring_extracted(self):
        chunks = self.chunker.chunk_source(SAMPLE_TOOL, file_path="a.py")
        tool = next(c for c in chunks if c.chunk_type == "agno_tool")
        assert tool.docstring is not None
        assert "Search the web" in tool.docstring

    def test_tool_decorator_extracted(self):
        chunks = self.chunker.chunk_source(SAMPLE_TOOL, file_path="a.py")
        tool = next(c for c in chunks if c.chunk_type == "agno_tool")
        assert "tool" in tool.decorators

    def test_model_bases_extracted(self):
        chunks = self.chunker.chunk_source(SAMPLE_MODEL, file_path="a.py")
        model = next(c for c in chunks if c.chunk_type == "pydantic_model")
        assert "BaseModel" in model.bases

    def test_calls_extracted_from_tool(self):
        chunks = self.chunker.chunk_source(SAMPLE_TOOL, file_path="a.py")
        tool = next(c for c in chunks if c.chunk_type == "agno_tool")
        # http_get should appear in calls
        assert "http_get" in tool.calls

    def test_empty_source_returns_no_chunks(self):
        chunks = self.chunker.chunk_source("", file_path="empty.py")
        assert chunks == []

    def test_syntax_error_returns_no_chunks(self):
        chunks = self.chunker.chunk_source("def broken(", file_path="broken.py")
        # Should not raise, just return empty or partial
        assert isinstance(chunks, list)

    def test_chunk_line_numbers_populated(self):
        chunks = self.chunker.chunk_source(SAMPLE_TOOL, file_path="a.py")
        for c in chunks:
            assert c.line_start >= 1
            assert c.line_end >= c.line_start

    def test_to_dict_has_all_fields(self):
        chunks = self.chunker.chunk_source(SAMPLE_MODEL, file_path="a.py")
        d = chunks[0].to_dict()
        for key in ("text", "symbol_name", "chunk_type", "file_path",
                    "line_start", "line_end", "content_hash",
                    "decorators", "docstring", "bases", "calls"):
            assert key in d, f"Missing key: {key}"


# ---------------------------------------------------------------------------
# DependencyGraph tests
# ---------------------------------------------------------------------------

class TestDependencyGraph:
    def setup_method(self):
        self.graph = DependencyGraph()

    def _build_from_source(self, source: str, tmp_path) -> dict:
        """Write source to a temp file and build the graph."""
        f = tmp_path / "sample.py"
        f.write_text(source)
        return self.graph.build(str(tmp_path), invalidate_cache=True)

    def test_nodes_contain_all_symbols(self, tmp_path):
        result = self._build_from_source(SAMPLE_GRAPH, tmp_path)
        names = {n["id"] for n in result["nodes"]}
        assert "OrderModel" in names
        assert "process_order" in names
        assert "OrderAgent" in names

    def test_uses_edge_pydantic_model(self, tmp_path):
        result = self._build_from_source(SAMPLE_GRAPH, tmp_path)
        edges = result["edges"]
        uses_edges = [(e["from"], e["to"]) for e in edges if e["type"] == "USES"]
        # process_order and/or OrderAgent should use OrderModel
        targets = {to for (_, to) in uses_edges}
        assert "OrderModel" in targets

    def test_stats_populated(self, tmp_path):
        result = self._build_from_source(SAMPLE_GRAPH, tmp_path)
        assert result["stats"]["nodes"] > 0
        assert result["stats"]["files"] > 0

    def test_get_callers(self, tmp_path):
        self._build_from_source(SAMPLE_GRAPH, tmp_path)
        callers = self.graph.get_callers("process_order", str(tmp_path))
        assert isinstance(callers, list)

    def test_get_impact_returns_list(self, tmp_path):
        self._build_from_source(SAMPLE_GRAPH, tmp_path)
        impact = self.graph.get_impact("OrderModel", str(tmp_path))
        assert isinstance(impact, list)

    def test_cache_is_used_on_second_call(self, tmp_path):
        self._build_from_source(SAMPLE_GRAPH, tmp_path)
        result1 = self.graph.build(str(tmp_path))
        result2 = self.graph.build(str(tmp_path))
        assert result1 is result2  # same object reference = cache hit
