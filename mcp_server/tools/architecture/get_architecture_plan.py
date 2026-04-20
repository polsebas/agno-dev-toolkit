"""
get_architecture_plan — MCP tool

Invocation triggers: any developer request involving building,
structuring, deploying, or understanding an Agno agent system.

Returns a full-stack architecture plan adapted to the use case.
"""
import logging
from typing import Any, Dict, List

from mcp_server.tools.architecture.agno_stack_knowledge import AGNO_STACK

logger = logging.getLogger("mcp.tool.get_architecture_plan")

# ---------------------------------------------------------------------------
# Intent detection keywords
# ---------------------------------------------------------------------------
_INTENT_SIGNALS: Dict[str, List[str]] = {
    "memory": ["memory", "history", "session", "persist", "storage"],
    "teams": ["team", "multi", "orchestrat", "delegate", "swarm", "router"],
    "deploy": ["deploy", "prod", "scale", "kubernetes", "docker"],
    "streaming": ["stream", "realtime", "chat", "sse", "websocket"],
    "human_in_the_loop": ["approval", "human", "review", "confirm"],
    "mcp": ["mcp", "ide", "cursor", "claude code"],
}


# ---------------------------------------------------------------------------
# Pattern recommendation logic
# ---------------------------------------------------------------------------
def _recommend_pattern(use_case_lower: str, detected: List[str]) -> str:
    """Pick the best agent pattern based on use case signals."""
    if "teams" in detected:
        if any(kw in use_case_lower for kw in ["debate", "swarm", "ambiguous"]):
            return "Swarm"
        return "Router"
    if any(kw in use_case_lower for kw in ["workflow", "pipeline", "linear", "step"]):
        return "Plan-and-Solve"
    if any(kw in use_case_lower for kw in ["dynamic", "react", "unknown"]):
        return "ReAct"
    # Default: most common pattern
    return "ReAct"


# ---------------------------------------------------------------------------
# Layer builders
# ---------------------------------------------------------------------------
def _build_sdk_layer(
    stack: dict,
    detected: List[str],
    complexity: str,
) -> dict:
    """Build the SDK layer section of the plan."""
    sdk = stack["layers"]["sdk"]
    components_list = ["Agent", "Tool"]
    key_decisions = [
        "Set max_num_calls=5 — circuit breaker mandatory",
    ]
    anti_patterns = list(sdk["components"]["Agent"]["anti_patterns"])

    canonical_examples: Dict[str, str] = {
        "Agent": sdk["components"]["Agent"]["canonical_example"],
        "Tool": sdk["components"]["Tool"]["canonical_example"],
    }

    # Memory
    if "memory" in detected:
        components_list.append("Memory")
        canonical_examples["Memory"] = sdk["components"]["Memory"]["canonical_example"]
        if complexity == "production":
            key_decisions.append(
                "Use PgAgentStorage — multi-session context detected"
            )
        else:
            key_decisions.append(
                "Use in-memory storage — local development mode"
            )

    # Teams
    if "teams" in detected:
        components_list.append("Teams")
        key_decisions.append(
            "Multi-agent orchestration detected — configure team pattern"
        )

    return {
        "components": components_list,
        "key_decisions": key_decisions,
        "canonical_examples": canonical_examples,
        "anti_patterns_to_avoid": anti_patterns,
    }


def _build_agent_os_layer(
    stack: dict,
    detected: List[str],
) -> dict:
    """Build the AgentOS layer section of the plan."""
    agent_os = stack["layers"]["agent_os"]
    components_list = ["async_rules"]
    key_decisions = [
        "All I/O must use httpx/asyncpg — no blocking calls",
    ]
    canonical_examples: Dict[str, str] = {}

    if "streaming" in detected:
        components_list.append("FastAPI_serving")
        key_decisions.append(
            "Use .astream() + StreamingResponse for real-time UX"
        )
        canonical_examples["FastAPI_serving"] = (
            agent_os["components"]["FastAPI_serving"]["canonical_example"]
        )

    if "human_in_the_loop" in detected:
        components_list.append("human_in_the_loop")
        key_decisions.append(
            "Add /prepare and /approve endpoints for destructive actions"
        )

    result: Dict[str, Any] = {
        "components": components_list,
        "key_decisions": key_decisions,
    }
    if canonical_examples:
        result["canonical_examples"] = canonical_examples
    return result


def _build_agno_ui_layer(stack: dict) -> dict:
    """Build the Agno UI layer section of the plan."""
    ui = stack["layers"]["agno_ui"]
    return {
        "components": list(ui["components"].keys()),
        "key_decisions": [
            "Use Playground for Day-1 local development",
            "AgentOS UI for production monitoring and tracing",
        ],
        "canonical_examples": {
            "Playground": ui["components"]["Playground"]["canonical_example"],
        },
    }


def _build_mcp_layer(stack: dict, detected: List[str]) -> dict:
    """Build the MCP layer section of the plan."""
    mcp = stack["layers"]["mcp_layer"]
    components_list = list(mcp["components"].keys())
    key_decisions = [
        "MCP server must start before agent — Connection Refused if reversed",
    ]

    if "mcp" in detected:
        key_decisions.append(
            "Configure stdio transport for IDE integration"
        )

    return {
        "components": components_list,
        "key_decisions": key_decisions,
        "canonical_examples": {
            "FastMCP_server": (
                mcp["components"]["FastMCP_server"]["canonical_example"]
            ),
        },
    }


def _build_infra_layer(stack: dict, detected: List[str]) -> dict:
    """Build the infrastructure layer section of the plan."""
    infra = stack["layers"]["infra"]
    key_decisions = list(infra["components"]["security"]["rules"])

    if "deploy" in detected:
        key_decisions.append(
            "Add GET /health endpoint validating DB + LLM reachability"
        )
        key_decisions.append("Use strict version pinning — agno==x.y.z")

    return {
        "components": list(infra["components"].keys()),
        "key_decisions": key_decisions,
    }


# ---------------------------------------------------------------------------
# Main run() entry point
# ---------------------------------------------------------------------------
async def run(args: dict) -> dict:
    """
    Return a full-stack architecture plan for building an Agno agent system.

    Args (via dict):
        use_case:    What the developer is building (required).
        layers:      Stack layers to include (default: all).
        complexity:  "simple" or "production" (default: "production").
    """
    use_case: str = args.get("use_case", "").strip()
    if not use_case:
        return _error(
            "INVALID_INPUT",
            "Provide 'use_case' describing what you are building.",
        )

    layers: List[str] = args.get(
        "layers", ["sdk", "agent_os", "agno_ui", "mcp_layer", "infra"]
    )
    complexity: str = args.get("complexity", "production")
    if complexity not in ("simple", "production"):
        complexity = "production"

    use_case_lower = use_case.lower()

    # ── 1. Detect intent signals ──────────────────────────────────────
    detected_patterns: List[str] = []
    for pattern_name, keywords in _INTENT_SIGNALS.items():
        if any(kw in use_case_lower for kw in keywords):
            detected_patterns.append(pattern_name)

    # ── 2. Agent pattern recommendation ───────────────────────────────
    recommended_pattern = _recommend_pattern(use_case_lower, detected_patterns)

    # ── 3. Build stack plan per layer ─────────────────────────────────
    stack_plan: Dict[str, Any] = {}

    if "sdk" in layers:
        stack_plan["sdk"] = _build_sdk_layer(
            AGNO_STACK, detected_patterns, complexity
        )

    if "agent_os" in layers:
        stack_plan["agent_os"] = _build_agent_os_layer(
            AGNO_STACK, detected_patterns
        )

    if "agno_ui" in layers:
        stack_plan["agno_ui"] = _build_agno_ui_layer(AGNO_STACK)

    if "mcp_layer" in layers:
        stack_plan["mcp_layer"] = _build_mcp_layer(
            AGNO_STACK, detected_patterns
        )

    if "infra" in layers and complexity != "simple":
        stack_plan["infra"] = _build_infra_layer(
            AGNO_STACK, detected_patterns
        )

    # ── 4. Simple complexity: strip production refs ───────────────────
    if complexity == "simple":
        # Remove PgAgentStorage references from SDK layer
        if "sdk" in stack_plan:
            sdk_section = stack_plan["sdk"]
            sdk_section["key_decisions"] = [
                d
                for d in sdk_section["key_decisions"]
                if "PgAgentStorage" not in d
            ]
            # Replace Memory example with in-memory default
            if "Memory" in sdk_section.get("canonical_examples", {}):
                sdk_section["canonical_examples"]["Memory"] = (
                    "# In-memory storage (default)\n"
                    "agent = Agent(\n"
                    "    add_history_to_messages=True,\n"
                    "    num_history_runs=5,\n"
                    ")"
                )

    # ── 5. Project structure ──────────────────────────────────────────
    project_structure = (
        AGNO_STACK["layers"]["infra"]["components"]["project_structure"]["canonical"]
    )

    # ── 6. Implementation order ───────────────────────────────────────
    implementation_order = [
        "1. Define Pydantic schemas in schemas/",
        "2. Implement tools in tools/ with typed params",
        "3. Write agent constitution in prompts/{role}_v1.md",
        "4. Define Agent with response_model + max_num_calls",
        "5. Test locally with Playground",
    ]
    if complexity == "production":
        implementation_order.extend([
            "6. Add PgAgentStorage + expose via FastAPI",
            "7. Add /health endpoint",
            "8. Configure MCP for IDE integration",
        ])

    # ── 7. Production checklist ───────────────────────────────────────
    production_checklist = list(AGNO_STACK["production_checklist"])
    if complexity == "simple":
        # Strip production-only items
        production_checklist = [
            item
            for item in production_checklist
            if "PgAgentStorage" not in item
            and "storage.create()" not in item
        ]

    # ── 8. Assemble final response ────────────────────────────────────
    plan = {
        "use_case": use_case,
        "detected_patterns": detected_patterns,
        "recommended_agent_pattern": recommended_pattern,
        "stack_plan": stack_plan,
        "project_structure": project_structure,
        "implementation_order": implementation_order,
        "production_checklist": production_checklist,
        "complexity": complexity,
    }

    logger.info(
        "Architecture plan generated for '%s' (complexity=%s, patterns=%s)",
        use_case,
        complexity,
        detected_patterns,
    )

    return {
        "success": True,
        "data": plan,
        "error": None,
        "meta": {
            "layers_included": list(stack_plan.keys()),
            "detected_patterns": detected_patterns,
            "complexity": complexity,
        },
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _error(code: str, message: str) -> dict:
    return {
        "success": False,
        "data": None,
        "error": {"code": code, "message": message},
        "meta": {},
    }
