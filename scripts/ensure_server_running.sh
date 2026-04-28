#!/usr/bin/env bash

# Script to start the MCP FastAPI server if it is not already running

# Change to the project root directory
cd "$(dirname "$0")/.."

# Check if the server is running
if pgrep -f "uvicorn.*mcp_server\.server:app" >/dev/null; then
    echo "MCP Server is already running."
    exit 0
fi

echo "MCP Server is not running. Starting it now..."

PORT=8001

# Start the server in the background using nohup
if [ -f "./.venv/bin/uvicorn" ]; then
    nohup ./.venv/bin/uvicorn mcp_server.server:app --host 0.0.0.0 --port $PORT > mcp_server.log 2>&1 &
else
    nohup uvicorn mcp_server.server:app --host 0.0.0.0 --port $PORT > mcp_server.log 2>&1 &
fi

echo "MCP Server started in the background on port $PORT. Logs are being written to mcp_server.log."
