from agno.agent import Agent
import time

# ❌ ANTI-PATTERN: Global mutable state
# Module-level mutable objects are shared across all requests.
shared_data = {}

def untyped_tool(param):
    """
    ❌ ANTI-PATTERN: Missing type hints.
    Agno needs type hints to generate correct JSON schemas for the tool.
    """
    return f"Processed {param}"

def slow_tool():
    # ❌ ANTI-PATTERN: Missing docstring (LLM won't know how to use it).
    # ❌ ANTI-PATTERN: Blocking time.sleep() instead of await asyncio.sleep().
    time.sleep(5)
    return "Done"

# ❌ ANTI-PATTERN: Missing tool_call_limit.
# Without this, the agent can loop infinitely if it gets confused.
agent = Agent(
    name="BrokenAgent",
    tools=[untyped_tool, slow_tool],
    # tool_call_limit=10  <- Missing!
)
