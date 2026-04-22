import ast
from validation.engine.validator import ValidationRule, ValidationIssue

class ToolDesignQualityRule(ValidationRule):
    rule_id = "TOOL_DESIGN_QUALITY"
    severity = "medium"
    description = "Checks that tools have docstrings and type hints."

    def check(self, tree: ast.AST, source: str) -> list[ValidationIssue]:
        issues = []
        # First, find all functions defined in the module
        functions = {}
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions[node.name] = node

        # Then, find Agent calls and inspect the tools list
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id == "Agent":
                    for kw in node.keywords:
                        if kw.arg == "tools" and isinstance(kw.value, ast.List):
                            for elt in kw.value.elts:
                                if isinstance(elt, ast.Name) and elt.id in functions:
                                    func_node = functions[elt.id]
                                    
                                    # Check for docstring
                                    docstring = ast.get_docstring(func_node)
                                    if not docstring:
                                        issues.append(ValidationIssue(
                                            rule=self.rule_id,
                                            severity="high",
                                            message=f"Tool '{elt.id}' missing docstring",
                                            detail=f"The LLM uses tool docstrings to decide when and how to use a tool. Without a docstring, the tool is invisible or confusing to the Agent.",
                                            line=elt.lineno,
                                            fix_hint=f"Add a descriptive docstring to the {elt.id} function."
                                        ))

                                    # Check for type hints in arguments
                                    has_untyped_arg = False
                                    for arg in func_node.args.args:
                                        if arg.arg != "self" and not arg.annotation:
                                            has_untyped_arg = True
                                            break
                                    
                                    if has_untyped_arg:
                                        issues.append(ValidationIssue(
                                            rule=self.rule_id,
                                            severity="medium",
                                            message=f"Tool '{elt.id}' has untyped arguments",
                                            detail=f"Agno uses Python type hints to generate JSON schemas for the tools. Untyped arguments can lead to incorrect tool calls.",
                                            line=elt.lineno,
                                            fix_hint=f"Add type hints to all arguments in the {elt.id} function."
                                        ))
        return issues
