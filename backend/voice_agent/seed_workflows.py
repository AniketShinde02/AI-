import asyncio
from core.database import db

SAMPLE_MISSIONS = [
  {
    "id": "m1",
    "name": "Morning Briefing",
    "trigger": "Daily at 08:00",
    "actions": ["Fetch news headlines", "Check calendar", "Summarize emails", "Read aloud"],
    "status": "active",
    "runs": 14,
    "lastRun": "Today, 08:00",
  },
  {
    "id": "m2",
    "name": "Web Research Pipeline",
    "trigger": "On voice command: 'research [topic]'",
    "actions": ["Web search", "Summarize results", "Save to memory"],
    "status": "active",
    "runs": 37,
    "lastRun": "2 hrs ago",
  },
  {
    "id": "m3",
    "name": "System Health Monitor",
    "trigger": "Every 30 minutes",
    "actions": ["Check CPU/RAM", "Alert if threshold exceeded"],
    "status": "paused",
    "runs": 88,
    "lastRun": "Yesterday",
  },
]

async def seed():
    print("Seeding workflows...")
    existing = await db.get_workflows()
    if len(existing) == 0:
        for mission in SAMPLE_MISSIONS:
            await db.create_workflow(mission)
            print(f"Created workflow: {mission['name']}")
    else:
        print(f"Database already has {len(existing)} workflows. Skipping seed.")

if __name__ == "__main__":
    asyncio.run(seed())
