import ast
from validation.engine.validator import ValidationRule, ValidationIssue

class LoopPreventionRule(ValidationRule):
    rule_id = "MISSING_TOOL_CALL_LIMIT"
    severity = "high"
    description = "Detects Agno Agents missing a tool_call_limit."

    def check(self, tree: ast.AST, source: str) -> list[ValidationIssue]:
        issues = []
        for node in ast.walk(tree):
            # Look for Agent(...) calls
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id == "Agent":
                    # Check if tool_call_limit is in keywords
                    has_limit = False
                    for kw in node.keywords:
                        if kw.arg == "tool_call_limit":
                            has_limit = True
                            break
                    
                    if not has_limit:
                        issues.append(ValidationIssue(
                            rule=self.rule_id,
                            severity=self.severity,
                            message="Agent missing tool_call_limit",
                            detail="Agno Agents should always specify a tool_call_limit (e.g. 10) to prevent infinite loops and runaway costs if the LLM gets stuck.",
                            line=node.lineno,
                            fix_hint="Add tool_call_limit=10 to the Agent constructor.",
                            suggested_code='agent = Agent(\n    ...,\n    tool_call_limit=10\n)'
                        ))
        return issues
