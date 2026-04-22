"""
Validation engine for Agno Dev Toolkit.

Architecture:
  ValidationRule (ABC) — base contract for all rules
  ValidationEngine   — runs rules, collects results
  ValidationIssue    — structured result type

Rules live in validation/rules/*.py and register themselves
via REGISTERED_RULES. The engine discovers them automatically.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
import ast


@dataclass
class ValidationIssue:
    rule: str
    severity: str          # "high" | "medium" | "low"
    message: str
    detail: str
    line: Optional[int] = None
    fix_hint: Optional[str] = None
    suggested_code: Optional[str] = None


class ValidationRule(ABC):
    """Base class for all validation rules."""
    
    rule_id: str           # e.g. "MISSING_CIRCUIT_BREAKER"
    severity: str          # "high" | "medium" | "low"
    description: str       # one-line description

    @abstractmethod
    def check(self, tree: ast.AST, source: str) -> list[ValidationIssue]:
        """
        Analyze the AST and return any issues found.
        Return empty list if the code is compliant.
        """
        ...


class ValidationEngine:
    """
    Runs all registered rules against a piece of Python code.
    Rules are auto-discovered from REGISTERED_RULES.
    """

    def __init__(self, rules: Optional[list[ValidationRule]] = None):
        if rules is not None:
            self.rules = rules
        else:
            # Auto-discover: import all rules to trigger registration
            from validation.rules import get_all_rules
            self.rules = get_all_rules()

    def validate(self, source: str) -> list[ValidationIssue]:
        """
        Parse source code and run all rules.
        Returns list of issues found (empty = compliant).
        On parse error, returns a single PARSE_ERROR issue.
        """
        try:
            tree = ast.parse(source)
        except SyntaxError as e:
            return [ValidationIssue(
                rule="PARSE_ERROR",
                severity="high",
                message="Code has a syntax error and cannot be analyzed",
                detail=str(e),
                line=e.lineno
            )]
        
        issues = []
        for rule in self.rules:
            issues.extend(rule.check(tree, source))
        return issues
