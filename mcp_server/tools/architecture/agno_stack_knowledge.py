"""
Agno Stack Knowledge Base

Complete static knowledge of the Agno stack used by the
get_architecture_plan tool to build full-stack architecture plans.

The LLM never sees this file directly — the tool uses it to build
the response.
"""

AGNO_STACK = {
    "layers": {
        "sdk": {
            "name": "Agno SDK",
            "description": "Core agent definition layer",
            "components": {
                "Agent": {
                    "purpose": "Core cognitive unit",
                    "required_params": ["model", "instructions"],
                    "production_params": [
                        "max_num_calls",
                        "response_model",
                        "tools",
                        "storage",
                    ],
                    "anti_patterns": [
                        "missing max_num_calls (no circuit breaker)",
                        "dict state instead of Pydantic BaseModel",
                        "hardcoded instructions instead of .md file",
                        "temperature > 0.0 with response_model",
                    ],
                    "canonical_example": (
                        "from agno.agent import Agent\n"
                        "from agno.models.anthropic import Claude\n"
                        "from pydantic import BaseModel\n"
                        "\n"
                        "class TicketResponse(BaseModel):\n"
                        "    action: str\n"
                        "    priority: str\n"
                        "    message: str\n"
                        "\n"
                        "agent = Agent(\n"
                        '    model=Claude(id="claude-sonnet-4-5"),\n'
                        '    instructions=open("prompts/support_v1.md").read(),\n'
                        "    tools=[query_tickets, escalate_ticket],\n"
                        "    response_model=TicketResponse,\n"
                        "    max_num_calls=5,\n"
                        ")"
                    ),
                },
                "Tool": {
                    "purpose": "Deterministic action layer",
                    "rules": [
                        "snake_case imperative names (process_ticket, not ProcessTicket)",
                        "docstring = cognitive directive for LLM, not code docs",
                        "all params typed for correct JSON Schema generation",
                        "never use time.sleep — use async/await",
                        "return dict with consistent schema",
                    ],
                    "canonical_example": (
                        "async def query_tickets(\n"
                        "    user_id: str,\n"
                        '    status: str = "open"\n'
                        ") -> dict:\n"
                        '    """\n'
                        "    Query support tickets for a user.\n"
                        "    Use this tool when the user asks about their open or\n"
                        "    resolved tickets. Always call before suggesting solutions.\n"
                        '    """\n'
                        "    async with httpx.AsyncClient() as client:\n"
                        "        response = await client.get(\n"
                        '            f"/api/tickets/{user_id}",\n'
                        '            params={"status": status}\n'
                        "        )\n"
                        "    return response.json()"
                    ),
                },
                "Memory": {
                    "purpose": "State persistence layer",
                    "environments": {
                        "development": "In-memory (default Agent())",
                        "production": "PgAgentStorage — mandatory for stateless HTTP",
                    },
                    "canonical_example": (
                        "from agno.storage.postgres import PgAgentStorage\n"
                        "\n"
                        "storage = PgAgentStorage(\n"
                        "    db_url=settings.database_url,\n"
                        '    table_name="agent_sessions"\n'
                        ")\n"
                        "storage.create()  # run before accepting requests\n"
                        "\n"
                        "agent = Agent(\n"
                        "    storage=storage,\n"
                        "    add_history_to_messages=True,\n"
                        "    num_history_runs=5,\n"
                        ")"
                    ),
                },
                "Teams": {
                    "purpose": "Multi-agent orchestration",
                    "patterns": {
                        "Router": "transfer_task() — handoff, router exits memory",
                        "Supervisor": "delegate_task() — supervisor keeps control",
                        "Swarm": "parallel debate with LLM-as-a-Judge resolution",
                    },
                },
            },
        },
        "agent_os": {
            "name": "AgentOS",
            "description": "Async runtime and serving layer",
            "components": {
                "FastAPI_serving": {
                    "purpose": "Expose agents via HTTP",
                    "rules": [
                        "use .astream() not .arun() for real-time UX",
                        "wrap in StreamingResponse for token-by-token output",
                        "never store state in agent instance attributes",
                        "isolate all session state in session_id",
                    ],
                    "canonical_example": (
                        "from fastapi import FastAPI\n"
                        "from fastapi.responses import StreamingResponse\n"
                        "from agno.agent import Agent\n"
                        "\n"
                        "app = FastAPI()\n"
                        "\n"
                        '@app.post("/chat")\n'
                        "async def chat(request: ChatRequest):\n"
                        "    async def generate():\n"
                        "        async for chunk in agent.astream(\n"
                        "            request.message,\n"
                        "            session_id=request.session_id\n"
                        "        ):\n"
                        '            yield f"data: {chunk}\\n\\n"\n'
                        "    return StreamingResponse(generate(),\n"
                        '                             media_type="text/event-stream")\n'
                        "\n"
                        '@app.get("/health")\n'
                        "async def health():\n"
                        '    return {"status": "ok", "storage": await storage.ping()}'
                    ),
                },
                "async_rules": {
                    "purpose": "Prevent event loop blocking",
                    "correct": ["httpx", "asyncpg", "aiofiles"],
                    "forbidden": [
                        "requests.get()",
                        "time.sleep()",
                        "open() inside async def",
                    ],
                },
                "human_in_the_loop": {
                    "purpose": "Approval workflow for destructive actions",
                    "pattern": (
                        "/prepare endpoint pauses PRAO cycle, "
                        "/approve resumes"
                    ),
                },
            },
        },
        "agno_ui": {
            "name": "Agno UI / Playground",
            "description": "Development monitoring and debugging layer",
            "components": {
                "Playground": {
                    "purpose": "Local development chat UI",
                    "when_to_use": "Day 1 — avoid curl friction",
                    "canonical_example": (
                        "from agno.playground import Playground\n"
                        "\n"
                        "app = Playground(agents=[support_agent]).get_app()\n"
                        "# uvicorn playground:app --reload"
                    ),
                },
                "AgentOS_UI": {
                    "purpose": "Production monitoring",
                    "capabilities": [
                        "Side-by-side prompt version comparison",
                        "Token cost per interaction",
                        "Latency per reasoning step",
                        "Full trace: prompt → tool calls → response",
                    ],
                },
            },
        },
        "mcp_layer": {
            "name": "MCP (Model Context Protocol)",
            "description": "IDE integration and tool extension layer",
            "components": {
                "stdio_transport": {
                    "purpose": "IDE integration (Cursor, Claude Code)",
                    "config_cursor": {
                        "command": "python",
                        "args": ["-m", "mcp_server.stdio_transport"],
                    },
                },
                "FastMCP_server": {
                    "purpose": "Custom tool exposure via MCP",
                    "rule": (
                        "MCP server must start before agent — "
                        "Connection Refused if reversed"
                    ),
                    "canonical_example": (
                        'from mcp.server.fastmcp import FastMCP\n'
                        '\n'
                        'mcp = FastMCP("my-toolkit")\n'
                        '\n'
                        "@mcp.tool()\n"
                        "async def validate_agent(filepath: str) -> dict:\n"
                        '    """Validate Agno agent architecture compliance."""\n'
                        "    return await run_validation(filepath)"
                    ),
                },
            },
        },
        "infra": {
            "name": "Infrastructure",
            "description": "Production deployment layer",
            "components": {
                "project_structure": {
                    "canonical": {
                        "agents/": "Cognitive layer — Agent definitions",
                        "tools/": "Action layer — deterministic functions",
                        "schemas/": "Contract layer — Pydantic models",
                        "prompts/": "Constitution layer — {role}_v{n}.md files",
                        "core/": "Orchestrator config — DB, timeouts",
                        "tests/": "QA — unit mocks + LLM-as-a-Judge",
                    }
                },
                "dependencies": {
                    "package_manager": "uv (preferred) or venv",
                    "mandatory": [
                        "agno",
                        "pydantic>=2",
                        "fastapi",
                        "httpx",
                        "asyncpg",
                    ],
                    "version_pinning": "strict — agno==x.y.z",
                },
                "database": {
                    "development": "SQLite or in-memory",
                    "production": "PostgreSQL via PgAgentStorage",
                    "init": "storage.create() before first request",
                },
                "security": {
                    "rules": [
                        ".env in .gitignore BEFORE creating the file",
                        ".env.example with empty keys — living onboarding doc",
                        "pydantic-settings BaseSettings for all config",
                        "never import os.environ directly in business logic",
                    ]
                },
                "health_check": {
                    "endpoint": "GET /health",
                    "must_validate": [
                        "database connection",
                        "LLM reachability",
                    ],
                    "purpose": "Kubernetes liveness probe",
                },
            },
        },
    },
    "decision_tree": {
        "choose_pattern": {
            "simple_qa_or_chatbot": "Single Agent + RAG",
            "linear_workflow": "Plan-and-Solve pattern, temperature=0.0",
            "dynamic_unknown_steps": "ReAct pattern",
            "multi_domain_routing": "Router Agent → Supervisor → Workers",
            "high_stakes_mutation": "Two-Phase Commit + Human-in-the-Loop",
            "ambiguous_complex_task": "Swarm (Debate) + LLM-as-a-Judge",
        },
        "choose_memory": {
            "single_session_dev": "In-memory default",
            "multi_session_prod": "PgAgentStorage",
            "knowledge_retrieval": (
                "RAG (vector) for unstructured, "
                "SQL for structured"
            ),
        },
        "choose_temperature": {
            "structured_output_or_tools": 0.0,
            "creative_or_debate": 0.7,
            "rule": "response_model present → always 0.0",
        },
    },
    "production_checklist": [
        "storage.create() called before API starts",
        "GET /health validates DB + LLM",
        "max_num_calls set on every agent",
        "all I/O uses httpx/asyncpg (no blocking calls)",
        "state isolated in session_id not agent instance",
        "response_model tied to temperature=0.0",
        ".env excluded from git",
        "prompts as .md files not hardcoded strings",
    ],
}
