from validation.rules.pydantic_rule import PydanticStateRule
from validation.rules.async_rule import AsyncBlockingRule
from validation.rules.state_rule import GlobalMutableStateRule
from validation.rules.loop_rule import LoopPreventionRule
from validation.rules.tool_design_rule import ToolDesignQualityRule

def get_all_rules():
    return [
        PydanticStateRule(),
        AsyncBlockingRule(),
        GlobalMutableStateRule(),
        LoopPreventionRule(),
        ToolDesignQualityRule(),
    ]
