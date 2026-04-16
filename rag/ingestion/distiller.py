import ast

class Distiller(ast.NodeTransformer):
    def visit_Assert(self, node):
        return None  # eliminar asserts

    def visit_Expr(self, node):
        # eliminar prints y logs básicos
        if isinstance(node.value, ast.Call):
            if getattr(node.value.func, "id", "") in ["print"]:
                return None
        return node


def distill(code: str):
    tree = ast.parse(code)
    tree = Distiller().visit(tree)
    ast.fix_missing_locations(tree)
    return ast.unparse(tree)
