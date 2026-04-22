import ast
from validation.engine.validator import ValidationRule, ValidationIssue

class AsyncBlockingRule(ValidationRule):
    rule_id = "ASYNC_REQUIRED"
    severity = "high"
    description = "Detects time.sleep() calls anywhere in the code."

    def check(self, tree: ast.AST, source: str) -> list[ValidationIssue]:
        issues = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                is_time_sleep = False
                if isinstance(func, ast.Attribute) and getattr(func.value, "id", "") == "time" and func.attr == "sleep":
                    is_time_sleep = True
                elif isinstance(func, ast.Name) and func.id == "sleep":
                    is_time_sleep = True
                    
                if is_time_sleep:
                    issues.append(ValidationIssue(
                        rule=self.rule_id,
                        severity=self.severity,
                        message="time.sleep() blocks the async event loop",
                        detail="In an async context, time.sleep() freezes all concurrent requests. Use await asyncio.sleep() instead.",
                        line=node.lineno,
                        fix_hint="await asyncio.sleep(seconds)",
                        suggested_code="import asyncio\nawait asyncio.sleep(1)"
                    ))
        return issues
