from validation.rules.pydantic_rule import PydanticStateRule
from validation.rules.async_rule import AsyncBlockingRule
from validation.rules.state_rule import GlobalMutableStateRule
from validation.rules.circuit_breaker_rule import CircuitBreakerRule

def get_all_rules():
    return [
        PydanticStateRule(),
        AsyncBlockingRule(),
        GlobalMutableStateRule(),
        CircuitBreakerRule(),
    ]
