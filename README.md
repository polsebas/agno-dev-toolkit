# Agno Dev Toolkit

MCP server that gives AI-assisted IDEs (Cursor, Claude Code) 
deep knowledge of the Agno framework — so the LLM suggests 
correct patterns instead of generic ones.

![Demo](https://via.placeholder.com/800x450.png?text=Agno+Dev+Toolkit+in+Action)
*Replace this with a 15-second demo GIF showing the LLM detecting architectural issues.*

## Quickstart

```bash
git clone https://github.com/polsebas/agno-dev-toolkit.git
cd agno-dev-toolkit
./start.sh
```

That's it. `start.sh` sets up the venv, installs deps, 
and indexes Agno's framework knowledge (~3 min first run).
The script prints the exact MCP config to paste into your IDE.

## What it does

Six tools the LLM uses automatically:

| Tool | What it does |
|------|-------------|
| `get_architecture_plan` | Full-stack Agno architecture plan for your use case |
| `validate_architecture_basics` | Detects anti-patterns: missing circuit breakers, blocking I/O, dict state |
| `explain_validation_failure` | Explains any validation issue with fix patterns |
| `query_framework_knowledge` | Semantic search over Agno's test suite |
| `read_project_graph` | Maps your project's classes and functions |
| `query_local_architecture` | Finds and returns any symbol definition in your project |

## Try it

Once connected, send these prompts in your IDE:
- *"I want to build an Agno agent for customer support"*
- *"Check this file for architecture issues"*
- *"How should I structure an Agno project from scratch?"*

## Requirements

- Python 3.10+
- Git (for cloning the Agno repo during setup)
- No Docker required

## Advanced: Milvus backend

ChromaDB is the default (no Docker). 
To use Milvus for larger deployments:

```bash
docker compose -f milvus-compose.yaml up -d
# Add to .env:
VECTOR_BACKEND=milvus
```

## Development

```bash
# Run tests
PYTHONPATH=. pytest tests/test_mcp_integration.py -v

# HTTP server (for debugging with curl)
bash scripts/run_server.sh
```
