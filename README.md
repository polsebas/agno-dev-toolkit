# Agno Dev Toolkit

The **Agno Dev Toolkit** is an MCP (Model Context Protocol) server designed to enforce architectural compliance and inject real framework knowledge into LLM-driven development workflows. 

It provides an awareness layer utilizing deep AST inspection and a vector-backed RAG infrastructure connected to the official framework tests.

## Features

- **MCP Tooling:** Exposes standard endpoints to interact with local code architecture and framework semantic searches.
- **RAG over Framework Tests:** Uses intelligent chunking and AST distillation to safely embed tests as high-signal contextual examples.
- **AST-Based Validation & Inspection:** Performs strict structural reviews (enforcing `BaseModel` and `async` logic) and explores local dependencies.
- **Milvus Vector Store Integration:** Lightweight but robust integration using `sentence-transformers` to locate components instantly.

## Available MCP Tools

* `validate_architecture_basics`: Checks code snippets or files for specific architectural rules (e.g. usage of Pydantic and asyncio).
* `read_project_graph`: Maps out the local Python project returning classes and types.
* `query_local_architecture`: Targets a specific identifier (like `schemas.user.UserSchema`) and resolves its raw source code and base dependencies.
* `query_framework_knowledge`: Triggers a semantic search in Milvus over the framework documentation logic.

## Getting Started

### 1. Environment Setup

Ensure you are inside the virtual environment and all requirements are installed:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Run Milvus Vector Database

The RAG architecture requires a running Milvus stack. You can start it locally via Docker:
```bash
wget https://github.com/milvus-io/milvus/releases/download/v2.4.17/milvus-standalone-docker-compose.yml -O milvus-compose.yaml
docker compose -f milvus-compose.yaml up -d
```

### 3. Ingest Framework Knowledge (RAG Pipeline)

Build the vector index by running the orchestrator. This clones the agno repository, extracts the AST from test scripts, eliminates noisy assertions, limits the chunk boundaries, and safely routes embeddings (`all-MiniLM-L6-v2`) inside Milvus.
```bash
python -m rag.ingestion.pipeline
```

### 4. Run the Server

Finally, run the backend server bridging MCP with Fast API:
```bash
bash scripts/run_server.sh
# Alternatively: uvicorn mcp_server.server:app --reload --port 8000
```
