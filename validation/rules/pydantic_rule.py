import ast
from validation.engine.validator import ValidationRule, ValidationIssue

class PydanticStateRule(ValidationRule):
    rule_id = "PYDANTIC_REQUIRED"
    severity = "high"
    description = "Detects raw dict literals assigned to variables that look like state containers."

    def check(self, tree: ast.AST, source: str) -> list[ValidationIssue]:
        issues = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                if isinstance(node.value, ast.Dict):
                    issues.append(ValidationIssue(
                        rule=self.rule_id,
                        severity=self.severity,
                        message="Raw dict used for state — use Pydantic BaseModel",
                        detail="Dict state fails silently on typos. Define a BaseModel with typed fields instead.",
                        line=getattr(node.targets[0], "lineno", None) if node.targets else getattr(node, "lineno", None),
                        fix_hint="class MyState(BaseModel):\n    field: str"
                    ))
        return issues
