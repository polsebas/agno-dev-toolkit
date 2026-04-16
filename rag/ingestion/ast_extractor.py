import ast

class TestExtractor(ast.NodeVisitor):
    def __init__(self):
        self.snippets = []

    def visit_FunctionDef(self, node):
        # solo funciones tipo test_
        if node.name.startswith("test_"):
            code = ast.unparse(node)
            self.snippets.append(code)

        self.generic_visit(node)

def extract_snippets(code: str):
    tree = ast.parse(code)
    extractor = TestExtractor()
    extractor.visit(tree)
    return extractor.snippets
