# 🛡️ Agno Dev Toolkit

**Validate, Debug, and Optimize Agno Agent Systems.**

Generic AI assistants (ChatGPT, Claude) are great at writing code, but they don't know your specific architecture rules. They'll happily suggest patterns that lead to infinite loops, unhandled edge cases, or "hallucinated" Agno tools.

Agno Dev Toolkit is an MCP server that turns your IDE into an **Agno Expert**. It doesn't just suggest code; it validatess your architecture against real-world Agno patterns and helps you build production-grade agent systems.

![Demo](https://via.placeholder.com/800x450.png?text=Agno+Dev+Toolkit+in+Action)

## 🚀 Quickstart (3 Minutes)

Zero config. Zero Docker. Just clone and run.

```bash
git clone https://github.com/polsebas/agno-dev-toolkit.git
cd agno-dev-toolkit
./start.sh
```

`start.sh` will:
1.  Set up a isolated Python environment.
2.  Index the latest Agno framework knowledge (via RAG over Agno's internal test suite).
3.  Provide the exact JSON to paste into your IDE (Cursor, Claude Desktop, VS Code).

## 🧠 Why use this?

| Feature | Generic LLM | Agno Dev Toolkit |
|---------|-------------|------------------|
| **Framework Knowledge** | May use outdated APIs | Grounded in Agno's latest test suite |
| **Safety** | Suggests loops & infinite logic | Detects missing `tool_call_limit` |
| **Observability** | Guessing | Real-time SQLite-based execution traces |
| **Architecture** | "Single file" scripts | Production-grade multi-agent patterns |

## 🛠️ The Toolkit

Once connected, your IDE gains these capabilities:

*   **`get_architecture_plan`**: Generates a full-stack plan for your agent use case.
*   **`validate_architecture_basics`**: Scans your code for "Shadow Loops", missing circuit breakers, and state leaks.
*   **`query_framework_knowledge`**: Semantic search specifically over Agno's implementation patterns.
*   **`explain_validation_failure`**: Don't just get an error; get a diff-style fix you can apply immediately.
*   **`read_project_graph`**: Scans the project structure to build a lightweight graph of files and top-level symbols.
*   **`query_local_architecture`**: Performs deep inspection of specific local symbols (e.g., Pydantic models), providing exact code definition and dependencies.
*   **`get_execution_traces`**: Retrieves real-time execution traces (SQLite-based) to capture and debug agent execution history.

## 🧪 Try it Out

Once setup, ask your IDE:
- *"I want to build a support agent that escalates to human if sentiment is low."*
- *"Check this agent file for potential infinite loops."*
- *"How do I implement a custom vector store in Agno?"*
- *"What are the dependencies of the `PgAgentStorage` model?"*
- *"Analyze the project structure and show me the main agents we have."*
- *"Show me the recent execution traces to find why the agent failed."*

## ⚙️ Requirements

- Python 3.10+
- `git`
- (Optional) Docker only if you want the Milvus backend.

## 🤝 Contributing

This is an emerging framework. If you find an anti-pattern we're missing, open a PR in `validation/rules/`.

