import logging
from typing import Dict, Any, List, Optional
import json

logger = logging.getLogger("nexus.model_router")

class ModelRouter:
    """
    Implements deterministic model routing for Nexus.
    Groq: Reasoning, Planning, Coding, Tool Execution, Standard Chat.
    Gemini Live: Real-time Audio/Video Streaming (handled separately in ws_main WebRTC hooks).
    """
    
    def __init__(self, groq_api_key: str, mistral_api_key: Optional[str] = None):
        self.groq_api_key = groq_api_key
        self.mistral_api_key = mistral_api_key
        self.groq_client: Any = None
        self.mistral_client: Any = None
        try:
            from groq import AsyncGroq
            self.groq_client = AsyncGroq(api_key=groq_api_key)
        except ImportError:
            logger.error("Groq library not found. Please install groq.")

        try:
            from mistralai.client import Mistral
            self.mistral_client = Mistral(api_key=mistral_api_key) if mistral_api_key else None
        except ImportError:
            logger.warning("Mistral library not found. Mistral routing disabled.")

    async def standard_chat(self, system_prompt: str, messages: List[Dict[str, str]], model: str = "llama-3.3-70b-versatile") -> str:
        """
        Standard text reasoning pipeline via Groq.
        """
        if not self.groq_client:
            return "Error: Groq client not initialized."
            
        formatted_messages = [{"role": "system", "content": system_prompt}] + messages
        
        # Route to Mistral if it's a mistral or pixtral model
        if "mistral" in model.lower() or "pixtral" in model.lower():
            if not self.mistral_client:
                return "Error: Mistral client not initialized. Check API key."
            try:
                # Use mistralai async client if available or sync depending on library version
                # assuming mistralai SDK v1.0.0+ 
                response = await self.mistral_client.chat.complete_async(
                    model=model,
                    messages=formatted_messages,
                    temperature=0.7,
                    max_tokens=1024,
                )
                content = response.choices[0].message.content
                return content if content is not None else ""
            except Exception as e:
                logger.error(f"Mistral API error: {e}")
                return f"Error: Failed to reach Mistral engine. Details: {str(e)}"
        
        # Default to Groq
        try:
            response = await self.groq_client.chat.completions.create(
                messages=formatted_messages,
                model=model,
                temperature=0.7,
                max_tokens=1024,
            )
            content = response.choices[0].message.content
            return content if content is not None else ""
        except Exception as e:
            logger.error(f"Groq API error: {e}")
            return f"Error: Failed to reach reasoning engine. Details: {str(e)}"

    async def execute_tool_call(self, user_intent: str, available_tools: List[Dict[str, Any]], model: str = "llama-3.3-70b-versatile") -> Dict[str, Any]:
        """
        Uses Groq strictly for fast, deterministic function calling based on user intent.
        """
        if not self.groq_client:
            return {"error": "Groq client not initialized."}
            
        messages = [
            {"role": "system", "content": "You are a precise function calling router. Call the appropriate tool based on the user's request. Do not add conversational fluff."},
            {"role": "user", "content": user_intent}
        ]
        
        try:
            response = await self.groq_client.chat.completions.create(
                messages=messages,
                model=model,
                tools=available_tools, # type: ignore
                tool_choice="auto",
                temperature=0.1
            )
            
            message = response.choices[0].message
            if message.tool_calls:
                tool_call = message.tool_calls[0]
                action = tool_call.function.name
                params = json.loads(tool_call.function.arguments)
                
                # Trace pipeline logging
                from core.database import db
                trace_log = {
                    "user_intent": user_intent,
                    "model_used": model,
                    "tool_selected": action
                }
                import asyncio
                asyncio.create_task(db.log_tool_audit(action, params, "routed", json.dumps(trace_log)))
                
                return {
                    "tool_name": action,
                    "arguments": params
                }
            else:
                return {"error": "No tool matched the intent."}
                
        except Exception as e:
            logger.error(f"Groq tool call error: {e}")
            return {"error": f"Tool routing failed: {str(e)}"}

# Singleton instance must be initialized with the API key in ws_main.py or config
model_router = None
