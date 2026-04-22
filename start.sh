#!/usr/bin/env bash
set -e

# Colors
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Parse arguments
DEMO_MODE=false
for arg in "$@"; do
    if [ "$arg" == "--demo" ]; then
        DEMO_MODE=true
    fi
done

echo -e "${CYAN}╔══════════════════════════════════════╗${NC}"
echo -e "${CYAN}║     Agno Dev Toolkit — Setup         ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════╝${NC}"

# 1. Check Python
echo -e "\n${YELLOW}[1/4] Checking Python...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: python3 not found. Please install Python 3.10+${NC}"
    exit 1
fi
PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
if (( $(echo "$PYTHON_VERSION < 3.10" | bc -l) )); then
    echo -e "${RED}Error: Python 3.10+ required (found $PYTHON_VERSION)${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Python $PYTHON_VERSION found${NC}"

# 2. Venv
echo -e "\n${YELLOW}[2/4] Setting up virtual environment...${NC}"
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    echo -e "${GREEN}✓ Created .venv${NC}"
else
    echo -e "${GREEN}✓ .venv already exists${NC}"
fi
source .venv/bin/activate

# 3. Dependencies  
echo -e "\n${YELLOW}[3/4] Installing dependencies...${NC}"
pip install --upgrade pip -q
pip install -r requirements.txt -q
echo -e "${GREEN}✓ Dependencies installed${NC}"

# 4. RAG ingestion
echo -e "\n${YELLOW}[4/4] Indexing Agno framework knowledge...${NC}"
DATA_DIR="data/chroma_db"
if [ -d "$DATA_DIR" ] && [ "$(ls -A $DATA_DIR 2>/dev/null)" ]; then
    echo -e "${GREEN}✓ Knowledge base already indexed — skipping${NC}"
else
    echo -e "   Cloning Agno repo and indexing test suite (~3 min)..."
    PYTHONPATH=. python -m rag.ingestion.pipeline
    echo -e "${GREEN}✓ Knowledge base ready${NC}"
fi

# Demo Mode
if [ "$DEMO_MODE" = true ]; then
    echo -e "\n${CYAN}⚡ Running Demo: Validation of 'example_project/broken_agent.py'...${NC}"
    if [ ! -f "example_project/broken_agent.py" ]; then
        echo -e "${RED}Error: example_project/broken_agent.py not found. Creating it now...${NC}"
        mkdir -p example_project
        cat > example_project/broken_agent.py <<EOF
from agno.agent import Agent
import time

# ANTI-PATTERN: Global mutable state
shared_data = {}

def slow_tool():
    """A tool that blocks the event loop."""
    # ANTI-PATTERN: Blocking I/O in a tool
    time.sleep(5)
    return "Done"

# ANTI-PATTERN: Missing tool_call_limit
agent = Agent(
    name="BrokenAgent",
    tools=[slow_tool],
    # tool_call_limit=10  <- Missing!
)
EOF
    fi
    echo -e "${YELLOW}Analyzing code for architectural flaws...${NC}"
    PYTHONPATH=. python -m mcp_server.tools.architecture.validate_architecture_basics --file example_project/broken_agent.py || true
    echo -e "\n${GREEN}Demo complete. See the issues detected above!${NC}"
fi

# Done
echo -e "\n${GREEN}╔══════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  ✓ Setup complete!                   ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════╝${NC}"

# Print IDE config
CURRENT_DIR=$(pwd)
echo -e "\n${CYAN}Connect to your IDE:${NC}"
echo -e "Add this to your MCP config (Cursor or Claude Code):\n"
echo '{
  "mcpServers": {
    "agno-dev-toolkit": {
      "command": "'"$CURRENT_DIR"'/.venv/bin/python",
      "args": ["-m", "mcp_server.stdio_transport"],
      "cwd": "'"$CURRENT_DIR"'"
    }
  }
}'

echo -e "\n${CYAN}Then try these prompts in your IDE:${NC}"
echo -e "  • \"I want to build an Agno agent for customer support\""
echo -e "  • \"Check this file for architecture issues\""
echo -e "  • \"How should I structure an Agno project?\"\n"
