import asyncio
from core.database import db

AGENTS = [
  {
    "id": "parent_delegate",
    "name": "parent_delegate_task",
    "status": "active",
    "description": "Top-level orchestrator. Decomposes complex instructions into sub-tasks and delegates.",
    "color": "#00FFFF",
    "runtime": "0.0s",
    "calls": 3,
  },
  {
    "id": "web_search",
    "name": "web_search",
    "status": "active",
    "description": "Real-time web intelligence. Executes Tavily queries and synthesizes results.",
    "color": "#6137FF",
    "runtime": "0.8s",
    "calls": 12,
  },
  {
    "id": "query_memory",
    "name": "query_memory",
    "status": "idle",
    "description": "Retrieves relevant context from persistent memory store.",
    "color": "#10b981",
    "runtime": "0.2s",
    "calls": 7,
  },
  {
    "id": "run_command",
    "name": "run_command",
    "status": "standby",
    "description": "System automation agent. Executes shell commands with sandboxing.",
    "color": "#f59e0b",
    "runtime": "—",
    "calls": 0,
  },
  {
    "id": "rag_oracle",
    "name": "rag_oracle",
    "status": "standby",
    "description": "Semantic retrieval from indexed knowledge base using vector similarity.",
    "color": "#ec4899",
    "runtime": "—",
    "calls": 0,
  },
]

async def seed():
    print("Seeding agents...")
    existing = await db.get_agents()
    if len(existing) == 0:
        for agent in AGENTS:
            await db.create_agent(agent)
            print(f"Created agent: {agent['name']}")
    else:
        print(f"Database already has {len(existing)} agents. Skipping seed.")

if __name__ == "__main__":
    asyncio.run(seed())
