import os
from analysis.ast.parser import ProjectSymbolParser

async def run(args: dict) -> dict:
    """
    Provides a lightweight overview of the project structure
    by scanning .py files and returning top-level classes and type hints.
    """
    directory = args.get("directory", ".")
    
    if not os.path.exists(directory):
        return {
            "success": False,
            "data": None,
            "error": {"code": "INVALID_DIRECTORY", "message": f"Directory not found: {directory}"},
            "meta": {}
        }

    try:
        parser = ProjectSymbolParser()
        project_graph = []
        
        for root, _, files in os.walk(directory):
            if "venv" in root or ".git" in root or "__pycache__" in root:
                continue
                
            for file in files:
                if file.endswith(".py"):
                    filepath = os.path.join(root, file)
                    symbols = parser.parse_file(filepath)
                    
                    if symbols:
                        class_symbols = [
                            {"name": sym["name"], "type_hint": sym["type_hint"]}
                            for sym in symbols if sym["type"] == "class"
                        ]
                        
                        if class_symbols:
                            project_graph.append({
                                "file": filepath,
                                "classes": class_symbols
                            })
                            
        return {
            "success": True,
            "data": {
                "graph": project_graph
            },
            "error": None,
            "meta": {
                "files_scanned": len(project_graph)
            }
        }
    except Exception as e:
        return {
            "success": False,
            "data": None,
            "error": {"code": "AST_PARSE_ERROR", "message": str(e)},
            "meta": {}
        }