async def run(args: dict):
    rule = args.get("rule", "")
    
    explanations = {
        "PYDANTIC_REQUIRED": "Pydantic is required for strict type validation to ensure architectural robustness.",
        "ASYNC_REQUIRED": "Synchronous functions like time.sleep block the event loop. Use asyncio.sleep instead."
    }

    return {
        "success": True,
        "data": {
            "rule": rule,
            "explanation": explanations.get(rule, f"No explanation available for rule: {rule}")
        },
        "error": None,
        "meta": {}
    }
