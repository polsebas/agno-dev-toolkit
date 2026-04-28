import os
import logging

# 1. Silence noisy transformers output by default.
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["TRANSFORMERS_VERBOSITY"] = "error"
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "0"

# 2. Load .env early — pydantic-settings only reads .env when Settings() is
#    instantiated, which happens *after* this module is already imported.
#    python-dotenv is already a transitive dep so this is safe.
try:
    from dotenv import load_dotenv as _load_dotenv
    _load_dotenv()  # searches CWD and parents for .env
except ImportError:
    pass  # dotenv not available; rely on shell env

# 3. Forward HF_TOKEN to the HF Hub client so all requests are authenticated
#    (higher rate limits, no unauthenticated-request warning).
_hf_token = os.environ.get("HF_TOKEN")
if _hf_token:
    # Both the modern and legacy env-var names are honoured by huggingface_hub.
    os.environ.setdefault("HUGGING_FACE_HUB_TOKEN", _hf_token)
    try:
        from huggingface_hub import login as _hf_login
        _hf_login(token=_hf_token, add_to_git_credential=False)
    except Exception:
        pass  # env var alone is sufficient if the API call fails

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

