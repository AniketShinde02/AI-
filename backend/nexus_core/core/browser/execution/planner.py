import json
import logging
from typing import Any, Dict, List, Optional
from core.browser.models import BrowserPlan, BrowserStep
from core.browser.skills.registry import skill_registry

logger = logging.getLogger("nexus.browser.execution.planner")

PLANNER_SYSTEM_PROMPT = """You are the Nexus V3 Browser Execution Planner.
Your job is to translate a user's high-level goal into a deterministic JSON sequence of browser actions.
Available actions: open_url, click, type, submit, search, wait, verify_text, scroll, extract, back, forward, refresh, select, verify_media.

You must reply with ONLY valid JSON representing the plan. Do not include markdown formatting or explanations.
Format:
{
    "goal": "the normalized goal",
    "steps": [
        {"action": "open_url", "target": "https://example.com"},
        {"action": "type", "target": "input#search", "value": "my query"},
        {"action": "click", "target": "button[type='submit']", "alt_targets": ["#submit-btn"]},
        {"action": "wait", "target": "networkidle"},
        {"action": "verify_text", "target": "Results for my query"}
    ]
}
Keep the steps as robust as possible. Provide alt_targets for clicks and types.
If the goal implies searching a known site, navigate directly to the search URL (e.g. youtube.com/results?search_query=) instead of typing in a search bar to save steps.
"""

class BrowserPlanner:
    """
    Generates a deterministic sequence of execution steps for a browser goal.
    Uses Skills Registry for fast-path execution, otherwise queries the LLM.
    """
    async def plan(self, goal: str, page: Any, extractor: Any) -> BrowserPlan:
        # 1. Fast Path: Skill Registry
        skill_plan = skill_registry.match_skill(goal)
        if skill_plan:
            logger.info(f"⚡ [Planner] Fast-tracking goal '{goal}' via skill '{skill_plan.skill_used}'")
            return skill_plan

        # 2. Extract current DOM state context to help the LLM plan
        logger.info(f"🧠 [Planner] No skill found for '{goal}'. Generating plan via LLM...")
        dom_result = await extractor.dom_snapshot(page)
        snap = dom_result.get("result", {})
        parts = []
        if snap.get("buttons"):
            parts.append("Buttons: " + " | ".join(f"[{b.get('text','?')}]({b.get('selector','')})" for b in snap["buttons"][:8]))
        if snap.get("inputs"):
            parts.append("Inputs: " + " | ".join(f"[{i.get('type','text')} name={i.get('name','')} id={i.get('id','')}]" for i in snap["inputs"][:6]))
        if snap.get("links"):
            parts.append("Links: " + " | ".join(f"[{lk.get('text','?')}]({lk.get('href','')})" for lk in snap["links"][:8] if lk.get("text"))[:400])

        current_state = f"URL: {page.url}\nTitle: {await page.title()}\n" + "\n".join(parts)

        # 3. Query LLM
        from core.provider.router import model_router, TaskClass
        
        prompt = f"GOAL: {goal}\n\nCURRENT DOM STATE:\n{current_state}\n\nGenerate the JSON plan:"
        try:
            raw_response = await model_router.route_task(
                task_class=TaskClass.BROWSER,
                system_prompt=PLANNER_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}]
            )
            
            # Clean JSON
            clean_json = raw_response
            if "```json" in clean_json:
                clean_json = clean_json.split("```json")[1].split("```")[0].strip()
            elif "```" in clean_json:
                clean_json = clean_json.split("```")[1].split("```")[0].strip()
                
            data = json.loads(clean_json)
            steps = []
            for s in data.get("steps", []):
                steps.append(BrowserStep(
                    action=s.get("action", ""),
                    target=s.get("target", ""),
                    value=s.get("value", ""),
                    alt_targets=s.get("alt_targets", []),
                    optional=s.get("optional", False)
                ))
            
            logger.info(f"✅ [Planner] Generated plan with {len(steps)} steps.")
            return BrowserPlan(goal=data.get("goal", goal), steps=steps)

        except Exception as e:
            logger.error(f"❌ [Planner] Failed to generate plan: {e}")
            # Fallback trivial plan
            return BrowserPlan(goal=goal, steps=[BrowserStep(action="search", target=goal)])

planner = BrowserPlanner()
