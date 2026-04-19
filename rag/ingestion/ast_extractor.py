import ast

class TestExtractor(ast.NodeVisitor):
    def __init__(self):
        self.snippets = []
        self.current_class = None
        self.current_setup = None

    def visit_ClassDef(self, node):
        old_class = self.current_class
        old_setup = self.current_setup
        
        self.current_class = node.name
        self.current_setup = None
        
        setup_code = []
        for child in node.body:
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and (child.name == 'setUp' or child.name.startswith('fixture_')):
                setup_code.append(ast.unparse(child))
        
        if setup_code:
            self.current_setup = "\n".join(setup_code)
            
        self.generic_visit(node)
        
        self.current_class = old_class
        self.current_setup = old_setup

    def _extract_function(self, node):
        if node.name.startswith("test_"):
            code = ast.unparse(node)
            
            if isinstance(node, ast.AsyncFunctionDef):
                node_copy = ast.AsyncFunctionDef(
                    name=node.name, args=node.args, body=[ast.Pass()],
                    decorator_list=node.decorator_list, returns=node.returns,
                    type_comment=getattr(node, 'type_comment', None)
                )
            else:
                node_copy = ast.FunctionDef(
                    name=node.name, args=node.args, body=[ast.Pass()],
                    decorator_list=node.decorator_list, returns=node.returns,
                    type_comment=getattr(node, 'type_comment', None)
                )
                
            ast.fix_missing_locations(node_copy)
            signature = ast.unparse(node_copy).replace("\n    pass", "").replace("\npass", "")
            
            self.snippets.append({
                "code": code,
                "class_name": self.current_class,
                "setup_code": self.current_setup,
                "signature": signature
            })

    def visit_FunctionDef(self, node):
        self._extract_function(node)
        self.generic_visit(node)
        
    def visit_AsyncFunctionDef(self, node):
        self._extract_function(node)
        self.generic_visit(node)

def extract_snippets(code: str):
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []
    extractor = TestExtractor()
    extractor.visit(tree)
    return extractor.snippets
