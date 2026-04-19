"""
DEMO FILE — intentional anti-patterns for Agno Dev Toolkit demonstration.

Run: validate_architecture_basics on this file to see detected issues.
Run: read_project_graph on example_project/ to see the full symbol map.
"""

# Anti-patterns present (intentional — for toolkit demo):
# 1. PYDANTIC_REQUIRED: session state stored as raw dict
# 2. ASYNC_REQUIRED: imports time (via email_tool which uses time.sleep)
# 3. MISSING: no max_num_calls (circuit breaker absent)
# 4. MISSING: no response_model with temperature=0.0

from agno.agent import Agent
# Note: this file intentionally has anti-patterns for toolkit demonstration

session_state = {          # ← PYDANTIC_REQUIRED: use SessionState(BaseModel)
    "user_id": None,
    "intent": None,
    "turns": 0
}

support_agent = Agent(
    instructions="You are a customer support agent. Help users with their issues.",
    # max_num_calls missing ← no circuit breaker
    # response_model missing ← no structured output contract
)
