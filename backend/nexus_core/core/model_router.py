"""
model_router.py
================
Phase 4 — Dynamic Capability Routing (Shadow Army Tier System)

Replaces the hardcoded single-provider routing with a full limit-aware,
multi-provider dispatcher keyed on TaskClass.

Shadow Army Tier Hierarchy:
  Monarch      → User / Jinwoo (HITL decisions)
  Grand Marshal → Mistral Large                 (heavy planning)
  Generals      → Cerebras 120B / Mistral       (fast browser loops)
  Knights       → Groq Llama 3.3-70B            (fast routing, chat)
  Eyes          → Gemini 1.5-flash / 2.0-flash  (vision)
  Shadow Soldiers → Mistral Small               (cheap background tasks)
  Infantry      → Local System / OpenRouter Free  (offline fallback)

TaskClass → Tier → Model mapping is defined in TIER_ROUTING_TABLE.
All existing callers of standard_chat() and execute_tool_call() are preserved.
"""

import logging
import json
import asyncio
import time
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Callable, Awaitable

import config

logger = logging.getLogger("nexus.model_router")


# =============================================================================
# 1. Enums & Data Structures
# =============================================================================

class TaskClass(str, Enum):
    FAST_ROUTING   = "FAST_ROUTING"    # Intent parsing, JSON extraction — sub-200ms
    CHAT           = "CHAT"            # Conversational turn — real-time voice
    PLANNING       = "PLANNING"        # Multi-step orchestration, Task Card planning
    BROWSER        = "BROWSER"         # Dense AXTree loops, web scraping
    PC_CONTROL     = "PC_CONTROL"      # OS commands, window management
    VISION         = "VISION"          # Screenshot OCR, element localization
    LONG_CONTEXT   = "LONG_CONTEXT"    # Large AXTree history, app log parsing
    CODE           = "CODE"            # Code generation / debugging
    RESEARCH       = "RESEARCH"        # RAG / large context scans
    CHEAP_TASK     = "CHEAP_TASK"      # Background minor tasks — "chndi kaam"


class AgentTier(str, Enum):
    GRAND_MARSHAL   = "Grand Marshal"
    GENERALS        = "Generals"
    KNIGHTS         = "Knights"
    EYES            = "Eyes"
    SHADOW_SOLDIERS = "Shadow Soldiers"
    INFANTRY        = "Infantry"


@dataclass
class TierConfig:
    tier: AgentTier
    provider: str                   # "groq" | "cerebras" | "mistral" | "gemini" | "openrouter"
    model: str
    max_tokens: int = 1024
    temperature: float = 0.4
    # Theme metadata broadcast to frontend
    theme_primary: str = "#18181b"
    theme_accent:  str = "#a1a1aa"


# =============================================================================
# 2. Routing Table — TaskClass → Primary TierConfig + Fallback chain
# =============================================================================

TIER_ROUTING_TABLE: Dict[TaskClass, List[TierConfig]] = {
    TaskClass.FAST_ROUTING: [
        TierConfig(AgentTier.KNIGHTS,       "groq",       "llama-3.1-8b-instant",                         max_tokens=256,  temperature=0.0, theme_primary="#1f1115", theme_accent="#ff3b30"),
        TierConfig(AgentTier.INFANTRY,       "openrouter", "meta-llama/llama-3.3-70b-instruct:free",       max_tokens=256,  temperature=0.0, theme_primary="#18181b", theme_accent="#a1a1aa"),
    ],
    TaskClass.CHAT: [
        TierConfig(AgentTier.KNIGHTS,        "groq",       "llama-3.3-70b-versatile",                      max_tokens=1024, temperature=0.5, theme_primary="#1f1115", theme_accent="#ff3b30"),
        TierConfig(AgentTier.INFANTRY,       "openrouter", "meta-llama/llama-3.3-70b-instruct:free",       max_tokens=1024, temperature=0.5, theme_primary="#18181b", theme_accent="#a1a1aa"),
    ],
    TaskClass.PLANNING: [
        TierConfig(AgentTier.GRAND_MARSHAL,  "mistral",    "mistral-large-latest",                         max_tokens=2048, temperature=0.3, theme_primary="#0b091a", theme_accent="#8a2be2"),
        TierConfig(AgentTier.KNIGHTS,        "groq",       "llama-3.3-70b-versatile",                      max_tokens=2048, temperature=0.3, theme_primary="#1f1115", theme_accent="#ff3b30"),
    ],
    TaskClass.BROWSER: [
        TierConfig(AgentTier.GENERALS,       "cerebras",   "llama3.1-70b",                                 max_tokens=2048, temperature=0.2, theme_primary="#0e1626", theme_accent="#00f0ff"),
        TierConfig(AgentTier.KNIGHTS,        "groq",       "llama-3.3-70b-versatile",                      max_tokens=2048, temperature=0.2, theme_primary="#1f1115", theme_accent="#ff3b30"),
    ],
    TaskClass.PC_CONTROL: [
        TierConfig(AgentTier.GENERALS,       "cerebras",   "llama3.1-70b",                                 max_tokens=1024, temperature=0.1, theme_primary="#0e1626", theme_accent="#00f0ff"),
        TierConfig(AgentTier.KNIGHTS,        "groq",       "llama-3.3-70b-versatile",                      max_tokens=1024, temperature=0.1, theme_primary="#1f1115", theme_accent="#ff3b30"),
    ],
    TaskClass.VISION: [
        TierConfig(AgentTier.EYES,           "gemini",     "gemini-1.5-flash",                             max_tokens=1024, temperature=0.3, theme_primary="#060f14", theme_accent="#00ff66"),
        TierConfig(AgentTier.EYES,           "gemini",     "gemini-2.0-flash",                             max_tokens=1024, temperature=0.3, theme_primary="#060f14", theme_accent="#00ff66"),
    ],
    TaskClass.LONG_CONTEXT: [
        TierConfig(AgentTier.GENERALS,       "cerebras",   "llama3.1-70b",                                 max_tokens=4096, temperature=0.3, theme_primary="#0e1626", theme_accent="#00f0ff"),
        TierConfig(AgentTier.EYES,           "gemini",     "gemini-1.5-flash",                             max_tokens=4096, temperature=0.3, theme_primary="#060f14", theme_accent="#00ff66"),
    ],
    TaskClass.CODE: [
        TierConfig(AgentTier.GRAND_MARSHAL,  "mistral",    "codestral-latest",                             max_tokens=2048, temperature=0.2, theme_primary="#0b091a", theme_accent="#8a2be2"),
        TierConfig(AgentTier.KNIGHTS,        "groq",       "llama-3.3-70b-versatile",                      max_tokens=2048, temperature=0.2, theme_primary="#1f1115", theme_accent="#ff3b30"),
    ],
    TaskClass.RESEARCH: [
        TierConfig(AgentTier.GENERALS,       "cerebras",   "llama3.3-70b",                                 max_tokens=4096, temperature=0.4, theme_primary="#0e1626", theme_accent="#00f0ff"),
        TierConfig(AgentTier.KNIGHTS,        "groq",       "mixtral-8x7b-32768",                           max_tokens=4096, temperature=0.4, theme_primary="#1f1115", theme_accent="#ff3b30"),
    ],
    TaskClass.CHEAP_TASK: [
        TierConfig(AgentTier.SHADOW_SOLDIERS,"mistral",    "mistral-small-latest",                         max_tokens=512,  temperature=0.5, theme_primary="#150d1a", theme_accent="#a855f7"),
        TierConfig(AgentTier.INFANTRY,       "openrouter", "meta-llama/llama-3.3-70b-instruct:free",       max_tokens=512,  temperature=0.5, theme_primary="#18181b", theme_accent="#a1a1aa"),
    ],
}


# =============================================================================
# 3. ModelRouter — Multi-client, Limit-Aware Dispatcher
# =============================================================================

class ModelRouter:
    """
    Limit-aware dynamic capability router implementing the Shadow Army tier system.

    Usage:
        response = await model_router.route_task(
            task_class=TaskClass.BROWSER,
            system_prompt="...",
            messages=[{"role": "user", "content": "..."}],
        )

    Backwards-compatible API preserved:
        response = await model_router.standard_chat(system_prompt, messages, model)
        result   = await model_router.execute_tool_call(user_intent, tools, model)
    """

    def __init__(self):
        self._groq_client       = None
        self._cerebras_client   = None
        self._mistral_client    = None
        self._gemini_client     = None
        self._openrouter_client = None
        self._initialized       = False

    def _init_clients(self) -> None:
        """Lazy initialization — only builds clients whose keys exist."""
        if self._initialized:
            return

        # Groq
        if config.GROQ_API_KEY:
            try:
                from groq import AsyncGroq
                self._groq_client = AsyncGroq(api_key=config.GROQ_API_KEY)
                logger.info("✅ [ModelRouter] Groq client initialized (Knights)")
            except ImportError:
                logger.warning("⚠️  [ModelRouter] groq library not installed.")

        # Cerebras (OpenAI-compatible endpoint)
        if config.CEREBRAS_API_KEY:
            try:
                from openai import AsyncOpenAI
                self._cerebras_client = AsyncOpenAI(
                    api_key=config.CEREBRAS_API_KEY,
                    base_url="https://api.cerebras.ai/v1",
                )
                logger.info("✅ [ModelRouter] Cerebras client initialized (Generals)")
            except ImportError:
                logger.warning("⚠️  [ModelRouter] openai library not installed — Cerebras unavailable.")

        # Mistral
        if config.MISTRAL_API_KEY:
            try:
                try:
                    from mistralai import Mistral  # type: ignore
                except ImportError:
                    from mistralai.client import Mistral  # type: ignore
                self._mistral_client = Mistral(api_key=config.MISTRAL_API_KEY)
                logger.info("✅ [ModelRouter] Mistral client initialized (Grand Marshal / Code)")
            except ImportError:
                logger.warning("⚠️  [ModelRouter] mistralai library not installed.")

        # Gemini (google-genai)
        if config.GEMINI_API_KEY:
            try:
                from google import genai
                self._gemini_client = genai.Client(api_key=config.GEMINI_API_KEY)
                logger.info("✅ [ModelRouter] Gemini client initialized (Eyes)")
            except ImportError:
                logger.warning("⚠️  [ModelRouter] google-genai library not installed.")

        # OpenRouter (OpenAI-compatible endpoint — Infantry fallback)
        if config.OPENROUTER_API_KEY:
            try:
                from openai import AsyncOpenAI
                self._openrouter_client = AsyncOpenAI(
                    api_key=config.OPENROUTER_API_KEY,
                    base_url="https://openrouter.ai/api/v1",
                )
                logger.info("✅ [ModelRouter] OpenRouter client initialized (Infantry fallback)")
            except ImportError:
                logger.warning("⚠️  [ModelRouter] openai library not installed — OpenRouter unavailable.")

        self._initialized = True

    def _get_client_for_provider(self, provider: str):
        """Returns the initialized client for a given provider string."""
        mapping = {
            "groq":       self._groq_client,
            "cerebras":   self._cerebras_client,
            "mistral":    self._mistral_client,
            "gemini":     self._gemini_client,
            "openrouter": self._openrouter_client,
        }
        return mapping.get(provider)

    async def _emit_theme(self, tier_cfg: TierConfig) -> None:
        """
        Broadcasts active agent tier to all connected WebSocket sessions.
        Frontend uses this to switch the Solo Leveling theme.
        Non-blocking — never raises.
        """
        try:
            from core.workspace.broadcast import broadcast_workspace_state
            import core.global_state as gs
            if not gs.active_sessions:
                return
            for session in list(gs.active_sessions.values()):
                if not session.is_connected:
                    continue
                await session.safe_send_json({
                    "type": "theme_update",
                    "data": {
                        "agent_tier":    tier_cfg.tier.value,
                        "provider":      tier_cfg.provider,
                        "model":         tier_cfg.model,
                        "theme_primary": tier_cfg.theme_primary,
                        "theme_accent":  tier_cfg.theme_accent,
                    }
                })
        except Exception as e:
            logger.debug(f"theme_update emit skipped: {e}")

    # -------------------------------------------------------------------------
    # Core Dispatcher — route_task()
    # -------------------------------------------------------------------------

    async def route_task(
        self,
        task_class: TaskClass,
        system_prompt: str,
        messages: List[Dict[str, str]],
        force_model: Optional[str] = None,
    ) -> str:
        """
        Main entry point. Selects the correct tier from TIER_ROUTING_TABLE and
        dispatches to the provider. Falls through the fallback chain on failure.

        Args:
            task_class:    What kind of task is this (BROWSER, PLANNING, etc.)
            system_prompt: System instruction string
            messages:      List of {"role": ..., "content": ...} dicts
            force_model:   Override model string (for backwards compat callers)

        Returns:
            Model response content string. Never raises — returns error string on
            total failure.
        """
        self._init_clients()

        if force_model == "gpt-oss-20b":
            force_model = "llama-3.1-8b-instant"
        elif force_model == "gpt-oss-120b":
            force_model = "llama3.1-70b"
        elif force_model == "models/gemini-2.0-flash-exp" or force_model == "gemini-2.5-flash-native-audio-dialog":
            force_model = "gemini-2.0-flash"

        tier_chain = TIER_ROUTING_TABLE.get(task_class, TIER_ROUTING_TABLE[TaskClass.CHAT])
        formatted  = [{"role": "system", "content": system_prompt}] + messages

        for tier_cfg in tier_chain:
            client = self._get_client_for_provider(tier_cfg.provider)
            if client is None:
                logger.debug(f"[ModelRouter] Skipping {tier_cfg.provider} — no API key / client.")
                continue

            model = force_model or tier_cfg.model
            logger.info(
                f"🎯 [ModelRouter] {task_class.value} → [{tier_cfg.tier.value}] "
                f"{tier_cfg.provider}/{model}"
            )

            try:
                # ── Provider Governor Integration ──
                from core.provider_governor import governor
                
                # Estimate token footprint (handle multimodal arrays gracefully)
                text_content = ""
                for m in formatted:
                    if isinstance(m.get("content"), str):
                        text_content += m["content"]
                    elif isinstance(m.get("content"), list):
                        for item in m["content"]:
                            if item.get("type") == "text":
                                text_content += item.get("text", "")
                
                estimated_tokens = len(text_content) // 4
                
                await governor.wait_if_needed(tier_cfg.provider, estimated_tokens)
                
                result = await self._dispatch(
                    client=client,
                    provider=tier_cfg.provider,
                    model=model,
                    messages=formatted,
                    max_tokens=tier_cfg.max_tokens,
                    temperature=tier_cfg.temperature,
                )
                # Fire-and-forget theme emission
                asyncio.create_task(self._emit_theme(tier_cfg))
                return result

            except Exception as e:
                err_str = str(e).lower()
                if "429" in err_str or "too many requests" in err_str:
                    logger.warning(
                        f"🔥 [ModelRouter] 429 Rate Limit hit on {tier_cfg.provider}/{model}. "
                        f"ProviderGovernor limit breached or server overloaded. Failing over..."
                    )
                    from core.workspace.broadcast import broadcast_workspace_state
                    asyncio.create_task(broadcast_workspace_state(
                        status="rate_limit_cooldown",
                        last_result=f"429 hit on {tier_cfg.provider}. Failing over to fallback tier..."
                    ))
                else:
                    logger.warning(
                        f"⚠️  [ModelRouter] {tier_cfg.provider}/{model} failed: {e}. "
                        f"Trying next fallback..."
                    )
                continue

        return "⚠️ All model providers failed or have no API keys configured. Check your .env file."

    async def _dispatch(
        self,
        client: Any,
        provider: str,
        model: str,
        messages: List[Dict[str, str]],
        max_tokens: int,
        temperature: float,
    ) -> str:
        """Routes to provider-specific call signature."""
        if provider == "groq":
            resp = await client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            content = resp.choices[0].message.content
            return content if content is not None else ""

        elif provider in ("cerebras", "openrouter"):
            # All use OpenAI-compatible async client
            resp = await client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            content = resp.choices[0].message.content
            return content if content is not None else ""

        elif provider == "mistral":
            resp = await client.chat.complete_async(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            content = resp.choices[0].message.content
            return content if content is not None else ""

        elif provider == "gemini":
            # google-genai aio generate_content
            system_msg = next((m["content"] for m in messages if m["role"] == "system" and isinstance(m["content"], str)), "")
            user_parts = []
            if system_msg:
                user_parts.append(system_msg)
                
            for m in messages:
                if m["role"] != "system":
                    if isinstance(m["content"], str):
                        user_parts.append(m["content"])
                    elif isinstance(m["content"], list):
                        for item in m["content"]:
                            if item.get("type") == "text":
                                user_parts.append(item.get("text", ""))
                            elif item.get("type") == "image_url":
                                b64 = item["image_url"]["url"].split(",")[-1]
                                import base64
                                from google.genai import types
                                user_parts.append(
                                    types.Part.from_bytes(
                                        data=base64.b64decode(b64),
                                        mime_type="image/jpeg"
                                    )
                                )

            resp = await client.aio.models.generate_content(
                model=model,
                contents=user_parts
            )
            return resp.text if resp.text else ""

        raise ValueError(f"Unknown provider: {provider}")

    # =========================================================================
    # Backwards-Compatible API — existing callers work unchanged
    # =========================================================================

    async def standard_chat(
        self,
        system_prompt: str,
        messages: List[Dict[str, str]],
        model: str = "llama-3.3-70b-versatile",
    ) -> str:
        """
        Legacy entrypoint. Routes via CHAT task class.
        model param is used as force_model override for exact backwards compat.
        """
        # Detect provider from model name to use correct task class
        task_class = TaskClass.CHAT
        if "codestral" in model or "code" in model.lower():
            task_class = TaskClass.CODE
        elif "mistral-large" in model or "405b" in model.lower():
            task_class = TaskClass.PLANNING

        return await self.route_task(
            task_class=task_class,
            system_prompt=system_prompt,
            messages=messages,
            force_model=model,
        )

    async def execute_tool_call(
        self,
        user_intent: str,
        available_tools: List[Dict[str, Any]],
        model: str = "llama-3.3-70b-versatile",
    ) -> Dict[str, Any]:
        """
        Legacy entrypoint for function-calling. Still routes via Groq directly
        since tool_choice support is most reliable there.
        """
        self._init_clients()

        if not self._groq_client:
            return {"error": "Groq client not initialized — GROQ_API_KEY missing."}

        messages = [
            {"role": "system", "content": "You are a precise function calling router. Call the appropriate tool based on the user's request. Do not add conversational fluff."},
            {"role": "user",   "content": user_intent},
        ]

        try:
            resp = await self._groq_client.chat.completions.create(
                messages=messages,
                model=model,
                tools=available_tools,  # type: ignore
                tool_choice="auto",
                temperature=0.1,
            )
            message = resp.choices[0].message
            if message.tool_calls:
                tool_call = message.tool_calls[0]
                action    = tool_call.function.name
                params    = json.loads(tool_call.function.arguments)

                from core.database import db
                asyncio.create_task(db.log_tool_audit(
                    action, params, "routed",
                    json.dumps({"user_intent": user_intent, "model_used": model, "tool_selected": action})
                ))
                return {"tool_name": action, "arguments": params}
            return {"error": "No tool matched the intent."}

        except Exception as e:
            logger.error(f"execute_tool_call failed: {e}")
            return {"error": f"Tool routing failed: {str(e)}"}


# =============================================================================
# Singleton — initialized on first use (lazy), never in import scope
# =============================================================================
model_router = ModelRouter()
