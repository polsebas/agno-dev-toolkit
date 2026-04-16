import ast


async def run(args: dict):
    code = args.get("code")
    filepath = args.get("filepath")
    mode = args.get("mode", "prototype")

    if not code and not filepath:
        return _error("INVALID_INPUT", "Provide 'code' or 'filepath'")

    if code and filepath:
        return _error("INVALID_INPUT_COMBINATION", "Use only one of 'code' or 'filepath'")

    try:
        if filepath:
            with open(filepath, "r") as f:
                code = f.read()

        tree = ast.parse(code)

        issues = []

        for node in ast.walk(tree):
            # Detect dict usage
            if isinstance(node, ast.Dict):
                issues.append({
                    "type": "WARNING" if mode == "prototype" else "CRITICAL",
                    "rule": "PYDANTIC_REQUIRED",
                    "message": "Dict detected. Use Pydantic BaseModel.",
                    "line": getattr(node, "lineno", None)
                })

            # Detect sync sleep
            if isinstance(node, ast.Call):
                if hasattr(node.func, "attr") and node.func.attr == "sleep":
                    issues.append({
                        "type": "CRITICAL",
                        "rule": "ASYNC_REQUIRED",
                        "message": "time.sleep detected. Use asyncio.sleep.",
                        "line": getattr(node, "lineno", None)
                    })

        return {
            "success": True,
            "data": {
                "valid": len([i for i in issues if i["type"] == "CRITICAL"]) == 0,
                "issues": issues
            },
            "error": None,
            "meta": {
                "mode": mode
            }
        }

    except Exception as e:
        return _error("AST_PARSE_ERROR", str(e))


def _error(code, message):
    return {
        "success": False,
        "data": None,
        "error": {
            "code": code,
            "message": message
        },
        "meta": {}
    }