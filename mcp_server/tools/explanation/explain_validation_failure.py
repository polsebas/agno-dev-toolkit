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
            "After:\n"
            "  from pydantic import BaseModel\n\n"
            "  class UserData(BaseModel):\n"
            "      name: str\n"
            "      age: int"
        ),
        "severity": "WARNING",
        "docs": "https://docs.pydantic.dev/latest/concepts/models/",
        "suggested_code": "class Result(BaseModel):\n    success: bool\n    message: str"
    },
    "ASYNC_REQUIRED": {
        "title": "Use asyncio.sleep instead of time.sleep",
        "explanation": (
            "time.sleep() blocks the entire event loop, freezing all "
            "concurrent tasks. In an async agent framework this can "
            "cause timeouts, stalled pipelines, and resource starvation."
        ),
        "fix": "Replace time.sleep with asyncio.sleep inside async functions.",
        "severity": "CRITICAL",
        "docs": "https://docs.python.org/3/library/asyncio-task.html#sleeping",
        "suggested_code": "import asyncio\nawait asyncio.sleep(1)"
    },
    "GLOBAL_STATE": {
        "title": "Avoid mutable global state",
        "explanation": (
            "Mutable global variables introduce hidden coupling between "
            "agents and tools, making the system difficult to test or scale."
        ),
        "fix": "Move state into a function context or a session-keyed store.",
        "severity": "WARNING",
        "docs": None,
        "suggested_code": "def my_tool(ctx: MyContext):\n    ctx.state['key'] = value"
    },
    "MISSING_TOOL_CALL_LIMIT": {
        "title": "Missing circuit breaker (tool_call_limit)",
        "explanation": (
            "Without tool_call_limit, an agent can loop indefinitely consuming tokens. "
            "This can lead to significant cost overruns and system instability."
        ),
        "fix": "Add tool_call_limit to your Agent instantiation.",
        "severity": "high",
        "docs": "https://docs.agno.com/agents/introduction",
        "suggested_code": "agent = Agent(\n    ...,\n    tool_call_limit=10\n)"
    },
    "TOOL_DESIGN_QUALITY": {
        "title": "Poor tool design (missing docs/hints)",
        "explanation": (
            "Tools without docstrings or type hints prevent the Agent "
            "from understanding how to use them correctly."
        ),
        "fix": "Add descriptive docstrings and Python type hints to all arguments.",
        "severity": "medium",
        "docs": "https://docs.agno.com/agents/tools",
        "suggested_code": "def my_tool(param: str) -> str:\n    \"\"\"Does something useful.\"\"\"\n    return param"
    },
    "PARSE_ERROR": {
        "title": "Parse Error",
        "explanation": "File could not be parsed, check syntax",
        "fix": "Fix python syntax errors.",
        "severity": "high",
        "docs": None,
    }
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
                "suggested_code": info.get("suggested_code")
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
