# Nexus Planner Skills Library

This document defines the official Planner automation skills supported by Nexus.
These skills represent advanced reasoning orchestration via `core.planner.compiler.PlannerCompiler`.

## 1. Complex Goal Execution (DAG Compilation)
- **Required Capabilities**: ANY combination.
- **Preconditions**: Request must be deemed "complex" by the Action Router.
- **Verification**: The Planner Compiler generates an acyclic graph of tool operations. Verification state cascades through dependent nodes in `executor.py`.
- **Recovery**: Individual node execution is wrapped by `wrap_execution` with exponential backoff. Node failure fails the execution sequence.
- **Example Prompt**: "Open Chrome, search for YouTube, click the first link, and maximize the window"

## 2. Pre-configured Task Cards (`run_task_card`)
- **Required Capabilities**: `run_task_card`
- **Preconditions**: The requested `card_id` must exist in `task_cards.json`.
- **Verification**: Verifies sequence completion in `task_card_engine`.
- **Recovery**: Fallback to basic agentic loop if predefined card fails halfway.
- **Example Prompt**: "Run the Google Maps Lead generator card for Austin"
