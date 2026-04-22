"""
Phase 2 integration tests for the Agno Dev Toolkit MCP Server.

Run with:
    pytest tests/test_mcp_integration.py -v
"""
import json
import pytest
from httpx import AsyncClient, ASGITransport

from mcp_server.server import app


@pytest.fixture
def transport():
    return ASGITransport(app=app)


@pytest.fixture
async def client(transport):
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def anyio_backend():
    return 'asyncio'



# ── Helper ──────────────────────────────────────────────────────────────────

def _parse_mcp(response) -> dict:
    """Extract the inner JSON payload from an MCP response."""
    body = response.json()
    assert "content" in body
    assert "isError" in body
    inner = json.loads(body["content"][0]["text"])
    return inner, body["isError"]


# ── Health & Discovery ──────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_health_returns_ok(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert isinstance(data["tools"], list)
    assert len(data["tools"]) == 7


@pytest.mark.anyio
async def test_tools_returns_schema(client):
    resp = await client.get("/tools")
    assert resp.status_code == 200
    data = resp.json()
    assert "tools" in data
    tool_names = [t["name"] for t in data["tools"]]
    assert "validate_architecture_basics" in tool_names
    assert "read_project_graph" in tool_names


# ── MCP Error Handling ──────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_missing_tool_field(client):
    resp = await client.post("/mcp", json={"arguments": {}})
    inner, is_error = _parse_mcp(resp)
    assert is_error is True
    assert inner["success"] is False
    assert "Missing" in inner["error"]["message"]


@pytest.mark.anyio
async def test_unknown_tool(client):
    resp = await client.post("/mcp", json={"tool": "nonexistent_tool"})
    inner, is_error = _parse_mcp(resp)
    assert is_error is True
    assert inner["success"] is False
    assert "Unknown tool" in inner["error"]["message"]


# ── validate_architecture_basics ────────────────────────────────────────────

@pytest.mark.anyio
async def test_validate_with_code_clean(client):
    code = "from pydantic import BaseModel\n\nclass User(BaseModel):\n    name: str\n"
    resp = await client.post(
        "/mcp",
        json={"tool": "validate_architecture_basics", "arguments": {"code": code}},
    )
    inner, is_error = _parse_mcp(resp)
    assert is_error is False
    assert inner["success"] is True
    assert inner["data"]["valid"] is True
    assert len(inner["data"]["issues"]) == 0


@pytest.mark.anyio
async def test_validate_with_code_issues(client):
    code = 'import time\n\ndef slow():\n    d = {"a": 1}\n    time.sleep(1)\n'
    resp = await client.post(
        "/mcp",
        json={"tool": "validate_architecture_basics", "arguments": {"code": code}},
    )
    inner, is_error = _parse_mcp(resp)
    assert is_error is False
    assert inner["success"] is True
    assert inner["data"]["valid"] is False
    rules = [i["rule"] for i in inner["data"]["issues"]]
    assert "PYDANTIC_REQUIRED" in rules
    assert "ASYNC_REQUIRED" in rules


@pytest.mark.anyio
async def test_validate_with_filepath(client):
    resp = await client.post(
        "/mcp",
        json={
            "tool": "validate_architecture_basics",
            "arguments": {"filepath": "mcp_server/server.py"},
        },
    )
    inner, is_error = _parse_mcp(resp)
    assert is_error is False
    assert inner["success"] is True
    assert "valid" in inner["data"]


@pytest.mark.anyio
async def test_validate_both_code_and_filepath_rejected(client):
    resp = await client.post(
        "/mcp",
        json={
            "tool": "validate_architecture_basics",
            "arguments": {"code": "x=1", "filepath": "some.py"},
        },
    )
    inner, is_error = _parse_mcp(resp)
    assert is_error is False  # Tool logic error, not server error
    assert inner["success"] is False
    assert inner["error"]["code"] == "INVALID_INPUT_COMBINATION"


@pytest.mark.anyio
async def test_validate_no_input_rejected(client):
    resp = await client.post(
        "/mcp",
        json={"tool": "validate_architecture_basics", "arguments": {}},
    )
    inner, is_error = _parse_mcp(resp)
    assert inner["success"] is False
    assert inner["error"]["code"] == "INVALID_INPUT"


# ── read_project_graph ──────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_read_project_graph_example(client):
    resp = await client.post(
        "/mcp",
        json={
            "tool": "read_project_graph",
            "arguments": {"path": "example_project"},
        },
    )
    inner, is_error = _parse_mcp(resp)
    assert is_error is False
    assert inner["success"] is True
    assert "graph" in inner["data"]


@pytest.mark.anyio
async def test_read_project_graph_bad_path(client):
    resp = await client.post(
        "/mcp",
        json={
            "tool": "read_project_graph",
            "arguments": {"path": "/nonexistent/path"},
        },
    )
    inner, is_error = _parse_mcp(resp)
    assert inner["success"] is False
    assert inner["error"]["code"] == "INVALID_DIRECTORY"


# ── query_local_architecture ────────────────────────────────────────────────

@pytest.mark.anyio
async def test_query_local_architecture_found(client):
    resp = await client.post(
        "/mcp",
        json={
            "tool": "query_local_architecture",
            "arguments": {"identifier": "ProjectSymbolParser", "directory": "."},
        },
    )
    inner, is_error = _parse_mcp(resp)
    assert is_error is False
    assert inner["success"] is True
    assert inner["data"]["identifier"] == "ProjectSymbolParser"
    assert inner["data"]["definition"] is not None


@pytest.mark.anyio
async def test_query_local_architecture_not_found(client):
    resp = await client.post(
        "/mcp",
        json={
            "tool": "query_local_architecture",
            "arguments": {"identifier": "NonExistentClass"},
        },
    )
    inner, is_error = _parse_mcp(resp)
    assert inner["success"] is False
    assert inner["error"]["code"] == "SYMBOL_NOT_FOUND"


@pytest.mark.anyio
async def test_query_local_architecture_compression(client):
    resp = await client.post(
        "/mcp",
        json={
            "tool": "query_local_architecture",
            "arguments": {
                "identifier": "ProjectSymbolParser",
                "directory": ".",
                "compression": "summarized",
            },
        },
    )
    inner, is_error = _parse_mcp(resp)
    assert is_error is False
    assert inner["success"] is True
    assert "..." in inner["data"]["definition"]
    assert inner["meta"]["compression"] == "summarized"


# ── explain_validation_failure ──────────────────────────────────────────────

@pytest.mark.anyio
async def test_explain_known_rules(client):
    resp = await client.post(
        "/mcp",
        json={
            "tool": "explain_validation_failure",
            "arguments": {
                "issues": [
                    {"rule": "PYDANTIC_REQUIRED", "line": 4},
                    {"rule": "ASYNC_REQUIRED", "line": 5},
                ]
            },
        },
    )
    inner, is_error = _parse_mcp(resp)
    assert is_error is False
    assert inner["success"] is True
    assert len(inner["data"]["explanations"]) == 2
    assert inner["data"]["explanations"][0]["title"] is not None
    assert inner["data"]["explanations"][0]["fix"] is not None


@pytest.mark.anyio
async def test_explain_unknown_rule(client):
    resp = await client.post(
        "/mcp",
        json={
            "tool": "explain_validation_failure",
            "arguments": {"issues": [{"rule": "MADE_UP_RULE"}]},
        },
    )
    inner, is_error = _parse_mcp(resp)
    assert inner["success"] is True
    assert inner["data"]["explanations"][0]["severity"] == "UNKNOWN"


@pytest.mark.anyio
async def test_explain_empty_issues_rejected(client):
    resp = await client.post(
        "/mcp",
        json={
            "tool": "explain_validation_failure",
            "arguments": {"issues": []},
        },
    )
    inner, is_error = _parse_mcp(resp)
    assert inner["success"] is False
    assert inner["error"]["code"] == "INVALID_INPUT"


# ── MCP response format validation ─────────────────────────────────────────

@pytest.mark.anyio
async def test_mcp_response_format_on_success(client):
    resp = await client.post(
        "/mcp",
        json={
            "tool": "validate_architecture_basics",
            "arguments": {"code": "x = 1"},
        },
    )
    body = resp.json()
    # Outer MCP envelope
    assert "content" in body
    assert isinstance(body["content"], list)
    assert body["content"][0]["type"] == "text"
    assert body["isError"] is False

    # Inner payload
    inner = json.loads(body["content"][0]["text"])
    assert "success" in inner
    assert "data" in inner
    assert "error" in inner
    assert "meta" in inner
    assert "latency_ms" in inner["meta"]
    assert "contract_version" in inner["meta"]


# ── get_architecture_plan ───────────────────────────────────────────────────

@pytest.mark.anyio
async def test_get_architecture_plan_basic(client):
    """Tool returns valid plan structure for a simple use case."""
    resp = await client.post(
        "/mcp",
        json={
            "tool": "get_architecture_plan",
            "arguments": {
                "use_case": "customer support agent with memory",
                "complexity": "production",
            },
        },
    )
    inner, is_error = _parse_mcp(resp)
    assert is_error is False
    assert inner["success"] is True
    plan = inner["data"]

    # Structure checks
    assert "stack_plan" in plan
    assert "sdk" in plan["stack_plan"]
    assert "implementation_order" in plan
    assert "production_checklist" in plan
    assert len(plan["production_checklist"]) > 0

    # Semantic checks — memory keyword must be detected
    assert "memory" in plan["detected_patterns"]
    assert "PgAgentStorage" in str(plan["stack_plan"]["sdk"])

    # Pattern selection
    assert plan["recommended_agent_pattern"] in [
        "ReAct", "Plan-and-Solve", "Router", "Swarm"
    ]


@pytest.mark.anyio
async def test_get_architecture_plan_simple_complexity(client):
    """Simple complexity strips infra and uses in-memory defaults."""
    resp = await client.post(
        "/mcp",
        json={
            "tool": "get_architecture_plan",
            "arguments": {
                "use_case": "quick prototype chatbot",
                "complexity": "simple",
            },
        },
    )
    inner, is_error = _parse_mcp(resp)
    assert is_error is False
    assert inner["success"] is True
    plan = inner["data"]
    assert plan["complexity"] == "simple"
    # Simple mode should NOT push PostgreSQL
    assert "PgAgentStorage" not in str(
        plan["stack_plan"].get("sdk", {})
    )
