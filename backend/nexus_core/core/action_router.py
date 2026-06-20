import json
import os
import logging
from typing import Dict, Any, Optional, List
import config

logger = logging.getLogger("nexus.action_router")

class ActionRouter:
    """
    Intercepts user intents using a fast Semantic Intent Classifier (Micro-LLM).
    Uses Dynamic Vocabulary Anchoring to eliminate brittle regex and ground STT hallucinations.
    Routes through model_router Shadow Army FAST_ROUTING tier (Knights → Shadow Soldiers → Infantry).
    """
    
    def __init__(self, fallback_apps: Optional[List[str]] = None):
        self.known_apps = fallback_apps or [
            "chrome", "whatsapp", "vs code", "spotify", "notepad", "terminal", "discord", "zoom"
        ]
        self._cache_loaded = False

    async def _load_cache(self):
        if self._cache_loaded:
            return
        try:
            from .database import db
            apps = await db.get_all_applications()
            if apps:
                self.known_apps = list(set(self.known_apps + apps))
            self._cache_loaded = True
            logger.info(f"ActionRouter loaded {len(self.known_apps)} apps into anchor dictionary.")
        except Exception as e:
            logger.error(f"Failed to load ActionRouter app cache: {e}")

    def _generate_system_prompt(self) -> str:
        apps_list_str = ", ".join([f"'{app}'" for app in self.known_apps])
        
        from core.capability_registry_def import ACTION_ROUTER_TOOL_NAMES
        tools_block = "\n".join(
            f"- {cap_id}" for cap_id in ACTION_ROUTER_TOOL_NAMES
        )
        
        from core.task_cards import task_card_engine
        cards = task_card_engine.list_cards()
        cards_list_str = ", ".join([f"'{card['card_id']}'" for card in cards])
        cards_details = "\n".join(
            f"- {card['card_id']} (inputs: {card['inputs']})" for card in cards
        )
        
        return f"""You are a fast semantic intent router for a PC automation system.
Analyze the user's input and determine if it maps to a computer control command or a pre-configured task card workflow.

Supported Tools:
{tools_block}

Target App Anchor Dictionary:
Known local apps include: [{apps_list_str}].

Target Task Cards Anchor Dictionary:
Known task cards include: [{cards_list_str}].
Details:
{cards_details}

Rules:
1. Handle Hinglish naturally (e.g., 'chrome open kro' -> tool: 'pc_open_app', target: 'chrome').
2. VOICE STT HALLUCINATION RULE: Voice transcribers frequently hallucinate phonetically.
   - Look at the Target App Anchor Dictionary and Target Task Cards Anchor Dictionary. If the transcribed word sounds highly similar to a known app or card in the context of the action, extract the exact word/id.
3. If the user requests to run/execute/start a pre-configured task card (e.g., 'Run Google Maps Leads card with Austin query', 'start doc_ppt_generation_v1 with notepad app_name'), set 'tool' to 'run_task_card' and 'target' to the matching card ID (e.g. 'google_maps_leads_v1' or 'doc_ppt_generation_v1').
4. If 'tool' is 'run_task_card', identify and extract any input parameters mentioned in the query (like 'query' or 'app_name') and place them as key-value pairs in the 'runtime_inputs' JSON object.
5. Assess your confidence (0-100) that the user is explicitly requesting a PC action/command/task card.
   - Clear commands/card requests should have confidence >= 85 (typically 90-100).
   - Conversational chat, random words, background noise ("Sikili Sikili"), ambiguous statements ("Shift ho raha hai"), or statements not matching supported tools must have confidence < 85 (typically < 50).
6. If the confidence is < 85, you should still populate the JSON but set "confidence" < 85. If it is conversational or doesn't fit the tools, tool should be "null".
7. You must reply ONLY with a single JSON object. Do not include markdown formatting like ```json.

Strict Output JSON Schema:
{{
  "tool": "tool_name_or_null",
  "target": "extracted_raw_app_name_or_text",
  "confidence": integer_score_0_to_100,
  "runtime_inputs": {{ ... }} // Optional key-value object of runtime parameter overrides if tool is 'run_task_card', otherwise null
}}"""

    async def route_intent(self, text: str) -> Optional[Dict[str, Any]]:
        # Ensure dynamic vocabulary anchor is loaded
        await self._load_cache()

        try:
            from core.model_router import model_router, TaskClass

            # FAST_ROUTING tier: Knights (Groq 8B) → Shadow Soldiers → Infantry
            # Returns a JSON string which we parse below
            raw_content = await model_router.route_task(
                task_class=TaskClass.FAST_ROUTING,
                system_prompt=self._generate_system_prompt(),
                messages=[{"role": "user", "content": f'Input: "{text}"'}],
            )
            result = json.loads(raw_content)
            tool = result.get("tool") or ""
            target = (result.get("target") or "").strip()
            try:
                confidence = int(result.get("confidence", 0))
            except (ValueError, TypeError):
                confidence = 0

            if confidence < 85:
                logger.info(f"🎯 [ACTION ROUTER] Confidence {confidence} < 85 threshold for '{text}' — treating as conversation")
                return None
            
            # Standardize string representations of null states
            if tool and tool not in ("null", "None"):
                # P2 STT SAFETY: Block destructive/keyboard actions when input is predominantly
                # Devanagari (Hindi/Marathi). "शिफ्ट हो रहा है" ≠ press Shift key.
                DESTRUCTIVE_TOOLS = {"pc_press_shortcut", "pc_type_text", "pc_close_app"}
                if tool in DESTRUCTIVE_TOOLS:
                    devanagari_chars = sum(1 for c in text if '\u0900' <= c <= '\u097f')
                    total_alpha = max(len([c for c in text if c.isalpha()]), 1)
                    devanagari_ratio = devanagari_chars / total_alpha
                    if devanagari_ratio > 0.30:
                        logger.warning(
                             f"🛡️ [STT Safety] Rejected '{tool}' for high-Devanagari input "
                            f"({devanagari_ratio:.0%} Devanagari): '{text[:60]}'"
                        )
                        return None  # Requires explicit English confirmation to execute
                return {
                    "intent": "ACTION",
                    "tool": tool,
                    "target": target,
                    "confidence": confidence,
                    "runtime_inputs": result.get("runtime_inputs")
                }
            return None
            
        except json.JSONDecodeError:
            logger.error("Failed to parse returned JSON schema from router LLM.")
            return None
        except Exception as e:
            logger.error(f"Semantic Action Router exception: {e}", exc_info=True)
            return None

# Instantiation
action_router = ActionRouter()
