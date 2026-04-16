from analysis.ast.parser import ProjectSymbolParser

async def run(args: dict) -> dict:
    """
    Retrieves the exact definition of a specific symbol (class or function)
    with dependencies and source code snippet.
    """
    identifier = args.get("identifier")
    directory = args.get("directory", ".")
    
    if not identifier:
        return {
            "success": False,
            "data": None,
            "error": {"code": "INVALID_INPUT", "message": "Provide 'identifier' to search for."},
            "meta": {}
        }

    try:
        parser = ProjectSymbolParser()
        symbol_info = parser.find_symbol(directory, identifier)
        
        if not symbol_info:
            return {
                "success": False,
                "data": None,
                "error": {"code": "SYMBOL_NOT_FOUND", "message": f"Could not find symbol: {identifier}"},
                "meta": {}
            }
            
        return {
            "success": True,
            "data": {
                "identifier": identifier,
                "filepath": symbol_info.get("filepath"),
                "definition": symbol_info.get("source"),
                "dependencies": symbol_info.get("bases", [])
            },
            "error": None,
            "meta": {}
        }
    except Exception as e:
        return {
            "success": False,
            "data": None,
            "error": {"code": "AST_PARSE_ERROR", "message": str(e)},
            "meta": {}
        }
