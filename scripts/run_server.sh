#!/usr/bin/env bash
uvicorn mcp_server.server:app --reload --port 8000
