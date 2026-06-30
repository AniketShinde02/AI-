import os
import json
import logging
from typing import Dict, Any, List, Optional
from core.browser_agent import browser_agent
from core.pc_control import pc_controller


logger = logging.getLogger("nexus.task_cards")


class TaskCardEngine:
    """
    Loads and executes dynamic Task Card configurations.
    Enforces pre-conditions, runs sequential steps, and checks verification contracts.
    """
    def __init__(self, catalog_dir: Optional[str] = None):
        if not catalog_dir:
            catalog_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "data", "task_cards"
            )
        self.catalog_dir = catalog_dir
        os.makedirs(self.catalog_dir, exist_ok=True)
        self._seed_default_cards()

    def _seed_default_cards(self):
        """Seed the B2B outreach and Freelance bidding demo cards if not present."""
        default_cards = {
            "google_maps_leads.json": {
                "card_id": "google_maps_leads_v1",
                "task_class": "BROWSER",
                "inputs": {
                    "query": "restaurants in Austin",
                    "output_file": "data/austin_restaurants.csv"
                },
                "workflow": [
                    { "step": 1, "action": "open_url", "target": "https://www.google.com/maps", "stop_on_fail": True },
                    { "step": 2, "action": "type", "target": "#searchboxinput", "text": "{query}", "stop_on_fail": True },
                    { "step": 3, "action": "click", "target": "#searchbox-searchbutton", "stop_on_fail": True }
                ]
            },
            "doc_ppt_generation.json": {
                "card_id": "doc_ppt_generation_v1",
                "task_class": "PC_CONTROL",
                "inputs": {
                    "app_name": "notepad"
                },
                "workflow": [
                    { "step": 1, "action": "open_app", "target": "{app_name}", "stop_on_fail": True },
                    { "step": 2, "action": "type_text", "text": "Nexus Dynamic Task Card Generation Report.\nSession Executed Successfully.", "stop_on_fail": True }
                ]
            }
        }
        for name, data in default_cards.items():
            path = os.path.join(self.catalog_dir, name)
            if not os.path.exists(path):
                try:
                    with open(path, "w", encoding="utf-8") as f:
                        json.dump(data, f, indent=2)
                except Exception as e:
                    logger.error(f"Failed to seed task card {name}: {e}")

    def load_card(self, card_id: str) -> Optional[Dict[str, Any]]:
        """Loads a task card by its ID from the catalog directory."""
        for filename in os.listdir(self.catalog_dir):
            if filename.endswith(".json"):
                path = os.path.join(self.catalog_dir, filename)
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if data.get("card_id") == card_id:
                            return data
                except Exception as e:
                    logger.error(f"Error reading task card {filename}: {e}")
        return None

    def list_cards(self) -> List[Dict[str, Any]]:
        """Lists metadata of all available task cards in the catalog."""
        cards = []
        for filename in os.listdir(self.catalog_dir):
            if filename.endswith(".json"):
                path = os.path.join(self.catalog_dir, filename)
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        cards.append({
                            "card_id": data.get("card_id"),
                            "task_class": data.get("task_class"),
                            "inputs": list(data.get("inputs", {}).keys()),
                            "steps_count": len(data.get("workflow", []))
                        })
                except Exception:
                    pass
        return cards

    async def execute_card(self, card_id: str, runtime_inputs: Dict[str, Any], session_id: str = "default") -> Dict[str, Any]:
        """Loads and executes a task card sequentially, checking step verification contracts."""
        card = self.load_card(card_id)
        if not card:
            return {"success": False, "error": f"Task card with ID '{card_id}' not found."}

        task_class = card.get("task_class", "BROWSER")
        workflow = card.get("workflow", [])
        
        # Merge default inputs with runtime overrides
        inputs = card.get("inputs", {})
        inputs.update(runtime_inputs)

        logger.info(f"⚙️ [TaskEngine] Running card '{card_id}' (class={task_class}) with inputs: {inputs}")

        # Execute Browser Workflow
        if task_class == "BROWSER":
            # Map workflow variables
            mapped_steps = []
            for step in workflow:
                mapped_step = step.copy()
                # Apply variable interpolations to target and text
                if isinstance(step.get("target"), str):
                    mapped_step["target"] = step["target"].format(**inputs)
                if isinstance(step.get("text"), str):
                    mapped_step["text"] = step["text"].format(**inputs)
                mapped_steps.append(mapped_step)

            # Delegate to BrowserAgent task executor
            res = await browser_agent.run_browser_task(
                goal=f"Task Card: {card_id}",
                steps=mapped_steps,
                session_id=session_id
            )
            return res

        # Execute PC Control Workflow
        elif task_class == "PC_CONTROL":
            results = []
            completed = 0
            total = len(workflow)

            for step in workflow:
                action = step.get("action")
                target = step.get("target", "")
                text = step.get("text", "")
                
                # Apply variable interpolations
                if isinstance(target, str):
                    target = target.format(**inputs)
                if isinstance(text, str):
                    text = text.format(**inputs)

                logger.info(f"  Step {step.get('step')}/{total}: {action}({target!r})")
                
                # Construct arguments for system execution wrapper
                params: Dict[str, Any] = {"session_id": session_id}
                if action == "open_app":
                    params["app_name"] = target
                elif action == "type_text":
                    params["text"] = text
                elif action == "press_shortcut":
                    params["keys"] = text.split("+")
                else:
                    params["target"] = target
                    params["text"] = text

                step_result: Dict[str, Any] = {"success": False, "verified": False}
                try:
                    from core.planner.executor import get_executor
                    executor = get_executor(f"pc_{action}")
                    if executor:
                        step_result = await executor.run(f"pc_{action}", params, max_retries=1, visual_verification=True)
                    else:
                        step_result = {"success": False, "error": f"Unknown capability pc_{action}", "verified": False}
                except Exception as e:
                    step_result["error"] = str(e)
                    logger.error(f"  Task card step failed: {e}")

                results.append(step_result)
                if step_result.get("success"):
                    completed += 1
                else:
                    logger.warning(f"  ❌ Step failed: {step_result.get('error')}")
                    if step.get("stop_on_fail", False):
                        logger.warning("  🛑 Stopping workflow execution (stop_on_fail=True)")
                        break

            overall_success = completed == total
            res_dict = {
                "success": overall_success,
                "verified": overall_success,
                "goal": f"Task Card: {card_id}",
                "steps_completed": completed,
                "steps_total": total,
                "results": results
            }
            if not overall_success and results:
                last_error = results[-1].get("error") or "Unknown step failure"
                res_dict["error"] = f"Step {completed + 1} failed: {last_error}"
            return res_dict

        return {"success": False, "error": f"Unsupported task class: {task_class}"}


# Singleton instance
task_card_engine = TaskCardEngine()
