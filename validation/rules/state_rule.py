import ast
from validation.engine.validator import ValidationRule, ValidationIssue

class GlobalMutableStateRule(ValidationRule):
    rule_id = "GLOBAL_STATE"
    severity = "medium"
    description = "Detects module-level mutable assignments."

    def check(self, tree: ast.AST, source: str) -> list[ValidationIssue]:
        issues = []
        # Walk top-level Assign nodes in the module body
        for node in tree.body:
            if isinstance(node, ast.Assign):
                if isinstance(node.value, (ast.Dict, ast.List, ast.Set)):
                    issues.append(ValidationIssue(
                        rule=self.rule_id,
                        severity=self.severity,
                        message="Mutable global state detected",
                        detail="Module-level mutable objects are shared across all requests in a concurrent server. Under load, User A's data will corrupt User B's session.",
                        line=getattr(node.targets[0], "lineno", None) if node.targets else getattr(node, "lineno", None),
                        fix_hint="Move state into the function scope or use session_id-keyed storage."
                    ))
        return issues
