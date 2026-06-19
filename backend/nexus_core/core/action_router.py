import json
import os
import logging
from typing import Dict, Any, Optional, List
from groq import AsyncGroq

logger = logging.getLogger("nexus.action_router")

class ActionRouter:
    """
    Intercepts user intents using a fast Semantic Intent Classifier (Micro-LLM).
    Uses Dynamic Vocabulary Anchoring to eliminate brittle regex and ground STT hallucinations.
    """
    
    def __init__(self, fallback_apps: Optional[List[str]] = None):
        self.client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY", ""))
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
        
        return f"""You are a fast semantic intent router for a PC automation system.
Analyze the user's input and determine if it maps to a computer control command.

Supported Tools:
{tools_block}

Target App Anchor Dictionary:
Known local apps include: [{apps_list_str}].

Rules:
1. Handle Hinglish naturally (e.g., 'chrome open kro' -> tool: 'pc_open_app', target: 'chrome').
2. VOICE STT HALLUCINATION RULE: Voice transcribers frequently hallucinate phonetically (e.g., 'close the water' instead of 'close whatsapp', 'open quote' instead of 'open code'). 
   - Look at the Target App Anchor Dictionary. If the transcribed word sounds highly similar to a known app in the context of the action, extract the exact word transcribed (e.g., "water", "quote"). Do not drop it. Our backend pipeline uses phonetic distance matching.
3. If the input is conversational chat, a general question, or doesn't fit the tools, return "null" for tool and "" for target.
4. You must reply ONLY with a single JSON object. Do not include markdown formatting like ```json.

Strict Output JSON Schema:
{{
  "tool": "tool_name_or_null",
  "target": "extracted_raw_app_name_or_text"
}}"""

    async def route_intent(self, text: str) -> Optional[Dict[str, Any]]:
        if not self.client.api_key:
            logger.warning("Groq API key missing. Skipping semantic routing.")
            return None

        # Ensure dynamic vocabulary anchor is loaded
        await self._load_cache()

        try:
            response = await self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": self._generate_system_prompt()},
                    {"role": "user", "content": f'Input: "{text}"'}
                ],
                model="llama-3.1-8b-instant",
                temperature=0.0,
                max_tokens=64,
                # Enforces structural JSON at the hardware inference level
                response_format={"type": "json_object"}
            )
            
            raw_content = response.choices[0].message.content
            if not raw_content:
                return None
                
            result = json.loads(raw_content)
            tool = result.get("tool")
            target = result.get("target", "").strip()
            
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
                    "target": target
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
