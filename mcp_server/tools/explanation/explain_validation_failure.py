import logging
from typing import List, Dict, Any

logger = logging.getLogger("mcp.tool.explain_validation_failure")

# ---------------------------------------------------------------------------
# Rule explanation catalogue
# ---------------------------------------------------------------------------
RULE_EXPLANATIONS: Dict[str, Dict[str, Any]] = {
    "PYDANTIC_REQUIRED": {
        "title": "Use Pydantic BaseModel instead of raw dict",
        "explanation": (
            "Raw dict usage bypasses type validation entirely. "
            "Pydantic BaseModel provides runtime type checking, "
            "serialization, and schema generation — all critical "
            "for agent-to-agent data contracts."
        ),
        "fix": (
            "Replace dict literals with a Pydantic BaseModel subclass.\n\n"
            "Before:\n"
            "  data = {\"name\": \"Alice\", \"age\": 30}\n\n"
            "After:\n"
            "  from pydantic import BaseModel\n\n"
            "  class UserData(BaseModel):\n"
            "      name: str\n"
            "      age: int\n\n"
            "  data = UserData(name=\"Alice\", age=30)"
        ),
        "severity": "WARNING (prototype) / CRITICAL (strict)",
        "docs": "https://docs.pydantic.dev/latest/concepts/models/",
    },
    "ASYNC_REQUIRED": {
        "title": "Use asyncio.sleep instead of time.sleep",
        "explanation": (
            "time.sleep() blocks the entire event loop, freezing all "
            "concurrent tasks. In an async agent framework this can "
            "cause timeouts, stalled pipelines, and resource starvation."
        ),
        "fix": (
            "Replace time.sleep with asyncio.sleep inside async functions.\n\n"
            "Before:\n"
            "  import time\n"
            "  time.sleep(5)\n\n"
            "After:\n"
            "  import asyncio\n"
            "  await asyncio.sleep(5)"
        ),
        "severity": "CRITICAL",
        "docs": "https://docs.python.org/3/library/asyncio-task.html#sleeping",
    },
    "GLOBAL_STATE": {
        "title": "Avoid mutable global state",
        "explanation": (
            "Mutable global variables introduce hidden coupling between "
            "agents and tools, making the system non-reproducible and "
            "difficult to test or scale horizontally."
        ),
        "fix": (
            "Move state into a dependency-injected context or "
            "a Pydantic settings object.\n\n"
            "Before:\n"
            "  counter = 0  # module-level mutable\n\n"
            "After:\n"
            "  from pydantic_settings import BaseSettings\n\n"
            "  class AppState(BaseSettings):\n"
            "      counter: int = 0"
        ),
        "severity": "WARNING",
        "docs": "https://docs.pydantic.dev/latest/concepts/pydantic_settings/",
    },
    "MISSING_TYPE_HINTS": {
        "title": "Add type hints to function signatures",
        "explanation": (
            "Functions without type hints reduce LLM comprehension of "
            "the codebase and prevent Pydantic from auto-generating "
            "schemas for tool inputs/outputs."
        ),
        "fix": (
            "Annotate all parameters and return types.\n\n"
            "Before:\n"
            "  def process(data):\n"
            "      return data\n\n"
            "After:\n"
            "  def process(data: UserData) -> ProcessedResult:\n"
            "      return ProcessedResult.from_raw(data)"
        ),
        "severity": "WARNING",
        "docs": "https://docs.python.org/3/library/typing.html",
    },
}


async def run(args: dict) -> dict:
    """
    Provide detailed explanations and fix patterns for validation
    issues returned by validate_architecture_basics.

    Accepts an 'issues' array where each item has at least a 'rule' key
    and an optional 'line' key.
    """
    issues: List[dict] = args.get("issues", [])

    if not issues:
        return _error(
            "INVALID_INPUT",
            "Provide 'issues' array with at least one item containing a 'rule' key.",
        )

    explanations = []
    for issue in issues:
        rule = issue.get("rule", "")
        line = issue.get("line")

        info = RULE_EXPLANATIONS.get(rule)

        if info:
            entry = {
                "rule": rule,
                "line": line,
                "title": info["title"],
                "explanation": info["explanation"],
                "fix": info["fix"],
                "severity": info["severity"],
                "docs": info["docs"],
            }
        else:
            entry = {
                "rule": rule,
                "line": line,
                "title": f"Unknown rule: {rule}",
                "explanation": f"No documentation available for rule '{rule}'.",
                "fix": None,
                "severity": "UNKNOWN",
                "docs": None,
            }

        explanations.append(entry)

    return {
        "success": True,
        "data": {
            "explanations": explanations,
        },
        "error": None,
        "meta": {
            "rules_explained": len(explanations),
            "rules_known": len([e for e in explanations if e["severity"] != "UNKNOWN"]),
        },
    }


def _error(code: str, message: str) -> dict:
    return {
        "success": False,
        "data": None,
        "error": {"code": code, "message": message},
        "meta": {},
    }
