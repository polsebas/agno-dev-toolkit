import ast
from validation.engine.validator import ValidationRule, ValidationIssue

class CircuitBreakerRule(ValidationRule):
    rule_id = "MISSING_CIRCUIT_BREAKER"
    severity = "high"
    description = "Detects Agent() instantiations without max_num_calls."

    def check(self, tree: ast.AST, source: str) -> list[ValidationIssue]:
        issues = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                is_agent = False
                if isinstance(func, ast.Name) and func.id == "Agent":
                    is_agent = True
                elif isinstance(func, ast.Attribute) and func.attr == "Agent":
                    is_agent = True
                    
                if is_agent:
                    has_max_num_calls = any(
                        isinstance(kw, ast.keyword) and kw.arg == "max_num_calls"
                        for kw in node.keywords
                    )
                    if not has_max_num_calls:
                        issues.append(ValidationIssue(
                            rule=self.rule_id,
                            severity=self.severity,
                            message="Agent instantiated without max_num_calls",
                            detail="Without max_num_calls, an agent can loop indefinitely consuming tokens and budget. This is the most common Agno production incident.",
                            line=getattr(node, "lineno", None),
                            fix_hint="Agent(..., max_num_calls=5)"
                        ))
        return issues
