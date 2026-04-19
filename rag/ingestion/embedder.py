import os
import sys
import logging

# 1. Environment variables for configuration
os.environ["TOKENIZERS_PARALLELISM"] = "false"
# Allow progress bars if user wants logs, but keep transformers quiet by default
os.environ["TRANSFORMERS_VERBOSITY"] = "error"
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "0"

# Note: In MCP mode, stdio_transport.py redirects stdout to stderr globally.
# This allows these logs to be visible in the console without breaking the JSON-RPC protocol.

try:
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer("all-MiniLM-L6-v2")
except Exception as e:
    logging.error("Failed to load SentenceTransformer: %s", e)
    model = None

def embed(texts):
    if model is None:
        return []
    return model.encode(texts).tolist()

