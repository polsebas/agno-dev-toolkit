#!/usr/bin/env bash
if [ -f "./.venv/bin/uvicorn" ]; then
    ./.venv/bin/uvicorn mcp_server.server:app --reload --port 8000
else
    uvicorn mcp_server.server:app --reload --port 8000
fi
