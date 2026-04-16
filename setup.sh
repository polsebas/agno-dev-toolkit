#!/usr/bin/env bash

set -e

PROJECT_NAME="agno-dev-toolkit"

echo "🚀 Creating project structure: $PROJECT_NAME"

# Root
mkdir -p $PROJECT_NAME
cd $PROJECT_NAME

# =========================
# Core MCP Server
# =========================
mkdir -p mcp_server/{routes,tools,core}

touch mcp_server/__init__.py
touch mcp_server/server.py
touch mcp_server/routes/__init__.py
touch mcp_server/routes/tools.py
touch mcp_server/core/__init__.py
touch mcp_server/core/registry.py

# =========================
# Tools Implementation
# =========================
mkdir -p mcp_server/tools/{project,rag,validation,explanation}

touch mcp_server/tools/__init__.py

touch mcp_server/tools/project/read_project_graph.py
touch mcp_server/tools/project/query_local_architecture.py

touch mcp_server/tools/rag/query_framework_knowledge.py

touch mcp_server/tools/validation/validate_architecture_basics.py

touch mcp_server/tools/explanation/explain_validation_failure.py

# =========================
# AST + Parsing Layer
# =========================
mkdir -p analysis/{ast,parsers}

touch analysis/__init__.py
touch analysis/ast/__init__.py
touch analysis/ast/parser.py
touch analysis/parsers/pydantic_parser.py

# =========================
# RAG Layer
# =========================
mkdir -p rag/{ingestion,retrieval,storage}

touch rag/__init__.py
touch rag/ingestion/ingest_tests.py
touch rag/retrieval/query_engine.py
touch rag/storage/vector_store.py

# =========================
# Validation Engine (PRAO base)
# =========================
mkdir -p validation/{rules,engine}

touch validation/__init__.py
touch validation/engine/validator.py

touch validation/rules/__init__.py
touch validation/rules/pydantic_rule.py
touch validation/rules/async_rule.py
touch validation/rules/state_rule.py

# =========================
# Config & Utils
# =========================
mkdir -p config utils

touch config/settings.py
touch utils/logger.py
touch utils/errors.py

# =========================
# Example Project (para testing local)
# =========================
mkdir -p example_project/{schemas,agents,tools}

touch example_project/schemas/user.py
touch example_project/agents/support_agent.py
touch example_project/tools/email_tool.py

# =========================
# Scripts
# =========================
mkdir -p scripts

touch scripts/run_server.sh
touch scripts/ingest_agno_tests.sh

# =========================
# Tests
# =========================
mkdir -p tests

touch tests/test_validator.py
touch tests/test_rag.py

# =========================
# Root Files
# =========================
touch README.md
touch .env
touch .gitignore
touch requirements.txt
touch pyproject.toml

# =========================
# Gitignore
# =========================
cat <<EOL > .gitignore
__pycache__/
*.pyc
.env
.venv/
.vscode/
*.log
EOL

# =========================
# Basic README
# =========================
cat <<EOL > README.md
# Agno Dev Toolkit

MCP server for enforcing architectural compliance and injecting real framework knowledge into LLM-driven development workflows.

## Features
- MCP Tooling
- RAG over framework tests
- AST-based validation
- Async + Pydantic enforcement

## Run
\`\`\`bash
bash scripts/run_server.sh
\`\`\`
EOL

# =========================
# Run script
# =========================
cat <<EOL > scripts/run_server.sh
#!/usr/bin/env bash
uvicorn mcp_server.server:app --reload --port 8000
EOL

chmod +x scripts/run_server.sh

# =========================
# Ingestion script placeholder
# =========================
cat <<EOL > scripts/ingest_agno_tests.sh
#!/usr/bin/env bash
echo "Ingesting Agno tests into vector store..."
# TODO: implementar pipeline RAG
EOL

chmod +x scripts/ingest_agno_tests.sh

# =========================
# Requirements (mínimo viable)
# =========================
cat <<EOL > requirements.txt
fastapi
uvicorn
pydantic>=2.0
httpx
qdrant-client
EOL

echo "✅ Project scaffold created successfully!"