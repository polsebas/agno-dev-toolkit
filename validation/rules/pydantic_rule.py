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
                        line=node.lineno,
                        fix_hint="class MyState(BaseModel):\n    field: str",
                        suggested_code="from pydantic import BaseModel\n\nclass State(BaseModel):\n    # Add typed fields here\n    pass"
                    ))
        return issues
