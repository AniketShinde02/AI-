# Gemini Agent Instructions (Truth Engine Integration)

## 🎯 Core Objective
Minimize token consumption and latency by prioritizing the **Code Review Graph (Truth Engine)** for codebase discovery, architectural analysis, and dependency mapping.

## 🛠️ Mandatory Workflow
1.  **Context Synchronization**: On your first turn in a new session, or after any code modification, run:
    ```powershell
    ./sync-context.ps1
    ```
2.  **Summary First**: Read `CONTEXT_SUMMARY.md` before exploring the file tree. It contains the most up-to-date entry points.
3.  **Wiki for Analysis**: Use the auto-generated wiki in `.code-review-graph/wiki/` to understand "communities" of code and how files relate.
    *   **NEVER** read multiple raw source files to understand an architecture if a wiki page covers it.
    *   Use `index.md` in the wiki to find the relevant logic group.

## 🧠 Efficiency Constraints
- **Zero Raw Analysis**: Do not perform "manual analysis" of the codebase by reading 10+ files. If the information is missing from the wiki, update the graph or ask for clarification.
- **Token Budget**: Every `view_file` call on a large file costs tokens. Use the wiki to find the *exact* function or block needed before reading the source.
- **Internal Knowledge**: Do not re-summarize the wiki back to the user unless explicitly asked. Use it as your internal mental map.

## 🔗 Key Assets
- **Wiki Root**: `./.code-review-graph/wiki/index.md`
- **tRPC API**: `./.planning/codebase/TRPC_API.md`
- **Boneyard Docs**: `./BONEYARD_GUIDELINES.md`
