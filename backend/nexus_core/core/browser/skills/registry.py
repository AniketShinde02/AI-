import os
import yaml
import logging
from typing import Dict, List, Optional
from core.browser.models import BrowserPlan, BrowserStep

logger = logging.getLogger("nexus.browser.skills.registry")

SKILLS_DIR = os.path.dirname(os.path.abspath(__file__))

class SkillRegistry:
    def __init__(self):
        self.skills = {}
        self._load_skills()

    def _load_skills(self):
        self.skills = {}
        if not os.path.exists(SKILLS_DIR):
            return
            
        for file in os.listdir(SKILLS_DIR):
            if file.endswith((".yaml", ".yml")):
                path = os.path.join(SKILLS_DIR, file)
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        data = yaml.safe_load(f)
                        if data and "name" in data and "steps" in data:
                            self.skills[data["name"].lower()] = data
                            logger.info(f"Loaded browser skill: {data['name']}")
                except Exception as e:
                    logger.error(f"Failed to load skill {file}: {e}")

    def match_skill(self, goal: str) -> Optional[BrowserPlan]:
        goal_lower = goal.lower()
        
        # Simple keyword matching for now
        for skill_name, data in self.skills.items():
            triggers = data.get("triggers", [])
            for trigger in triggers:
                if trigger.lower() in goal_lower:
                    logger.info(f"Goal '{goal}' matched skill '{skill_name}' via trigger '{trigger}'")
                    steps = []
                    for step_dict in data.get("steps", []):
                        steps.append(BrowserStep(
                            action=step_dict.get("action", ""),
                            target=step_dict.get("target", ""),
                            value=step_dict.get("value", ""),
                            alt_targets=step_dict.get("alt_targets", []),
                            optional=step_dict.get("optional", False)
                        ))
                    
                    return BrowserPlan(
                        goal=goal,
                        skill_used=skill_name,
                        steps=steps
                    )
        
        return None

# Singleton
skill_registry = SkillRegistry()
