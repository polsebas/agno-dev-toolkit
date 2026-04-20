#!/usr/bin/env bash
set -e

CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${CYAN}╔══════════════════════════════════════╗${NC}"
echo -e "${CYAN}║     Agno Dev Toolkit — Setup         ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════╝${NC}"

# 1. Check Python
echo -e "\n${YELLOW}[1/4] Checking Python...${NC}"
python3 --version || { echo -e "${RED}Python 3.10+ required${NC}"; exit 1; }

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
pip install -r requirements.txt -q
echo -e "${GREEN}✓ Dependencies installed${NC}"

# 4. RAG ingestion
echo -e "\n${YELLOW}[4/4] Indexing Agno framework knowledge...${NC}"
DATA_DIR="data/chroma_db"
if [ -d "$DATA_DIR" ] && [ "$(ls -A $DATA_DIR 2>/dev/null)" ]; then
    echo -e "${GREEN}✓ Knowledge base already indexed — skipping${NC}"
    echo -e "   (Delete data/chroma_db to force re-index)"
else
    echo -e "   Cloning Agno repo and indexing test suite (~3 min)..."
    PYTHONPATH=. python -m rag.ingestion.pipeline
    echo -e "${GREEN}✓ Knowledge base ready${NC}"
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
