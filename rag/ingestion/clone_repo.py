import subprocess
import os

REPO_URL = "https://github.com/agno-agi/agno.git"
CLONE_PATH = "data/agno_repo"

def clone_repo():
    if os.path.exists(CLONE_PATH):
        return CLONE_PATH
        
    os.makedirs("data", exist_ok=True)
    subprocess.run(["git", "clone", REPO_URL, CLONE_PATH], check=True)
    return CLONE_PATH
