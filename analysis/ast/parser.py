import ast
import os
from typing import List, Dict, Any

class ProjectSymbolParser:
    """
    AST parser to extract structural elements (classes, functions)
    from local python source files.
    """
    def __init__(self):
        pass

    def parse_file(self, filepath: str) -> List[Dict[str, Any]]:
        """Parses a single file and extracts its symbols."""
        symbols = []
        if not os.path.exists(filepath):
            return symbols
            
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                source = f.read()
            tree = ast.parse(source)
            
            for node in tree.body:
                if isinstance(node, ast.ClassDef):
                    base_classes = []
                    for base in node.bases:
                        if isinstance(base, ast.Name):
                            base_classes.append(base.id)
                        elif isinstance(base, ast.Attribute):
                            base_classes.append(base.attr)
                            
                    type_hint = "unknown"
                    if "BaseModel" in base_classes:
                        type_hint = "pydantic_model"
                    elif "Agent" in base_classes or "Agent" in node.name:
                        type_hint = "agent"
                    elif "Tool" in base_classes or "Tool" in node.name:
                        type_hint = "tool"
                        
                    source_segment = ast.get_source_segment(source, node)
                    
                    symbols.append({
                        "name": node.name,
                        "type": "class",
                        "type_hint": type_hint,
                        "bases": base_classes,
                        "source": source_segment,
                    })
                elif isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                    source_segment = ast.get_source_segment(source, node)
                    
                    type_hint = "function"
                    if "tool" in node.name.lower():
                        type_hint = "tool"
                        
                    symbols.append({
                        "name": node.name,
                        "type": "function",
                        "type_hint": type_hint,
                        "bases": [],
                        "source": source_segment,
                    })
        except Exception as e:
            # Silently skip unparseable files
            pass
            
        return symbols

    def find_symbol(self, project_root: str, identifier: str) -> Dict[str, Any]:
        """
        Locates a symbol by identifier (e.g. schemas.user.UserSchema or UserSchema)
        and returns its definition.
        """
        target_name = identifier.split('.')[-1]
        
        for root, _, files in os.walk(project_root):
            if "venv" in root or ".git" in root or "__pycache__" in root:
                continue
            for file in files:
                if file.endswith('.py'):
                    filepath = os.path.join(root, file)
                    symbols = self.parse_file(filepath)
                    for sym in symbols:
                        if sym["name"] == target_name:
                            sym["filepath"] = filepath
                            return sym
        return {}
