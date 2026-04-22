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

        from validation.engine.validator import ValidationEngine
        engine = ValidationEngine()
        
        raw_issues = engine.validate(code)
        issues = []
        
        for issue in raw_issues:
            if mode == "prototype" and issue.rule == "GLOBAL_STATE":
                continue
            issues.append({
                "rule": issue.rule,
                "severity": issue.severity,
                "message": issue.message,
                "detail": issue.detail,
                "line": issue.line,
                "fix_hint": issue.fix_hint,
                "suggested_code": issue.suggested_code
            })

        return {
            "success": True,
            "data": {
                "valid": len([i for i in issues if i["severity"] == "high"]) == 0,
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


if __name__ == "__main__":
    import argparse
    import asyncio
    import json
    import sys

    parser = argparse.ArgumentParser(description="Validate Agno architecture")
    parser.add_argument("--file", help="Path to Python file")
    parser.add_argument("--code", help="Raw Python code")
    parser.add_argument("--mode", default="prototype", help="Validation mode (prototype|strict)")

    args = parser.parse_args()
    
    run_args = {
        "mode": args.mode
    }
    if args.file:
        run_args["filepath"] = args.file
    if args.code:
        run_args["code"] = args.code

    result = asyncio.run(run(run_args))
    print(json.dumps(result, indent=2))
    
    if not result.get("success") or not result["data"].get("valid"):
        sys.exit(1)