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
    
    def __init__(self, groq_api_key: str):
        self.groq_api_key = groq_api_key
        try:
            from groq import AsyncGroq
            self.groq_client = AsyncGroq(api_key=groq_api_key)
        except ImportError:
            logger.error("Groq library not found. Please install groq.")
            self.groq_client = None

    async def standard_chat(self, system_prompt: str, messages: List[Dict[str, str]], model: str = "llama-3.3-70b-versatile") -> str:
        """
        Standard text reasoning pipeline via Groq.
        """
        if not self.groq_client:
            return "Error: Groq client not initialized."
            
        formatted_messages = [{"role": "system", "content": system_prompt}] + messages
        
        try:
            response = await self.groq_client.chat.completions.create(
                messages=formatted_messages,
                model=model,
                temperature=0.7,
                max_tokens=1024,
            )
            return response.choices[0].message.content
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
                tools=available_tools,
                tool_choice="auto",
                temperature=0.1
            )
            
            message = response.choices[0].message
            if message.tool_calls:
                tool_call = message.tool_calls[0]
                return {
                    "tool_name": tool_call.function.name,
                    "arguments": json.loads(tool_call.function.arguments)
                }
            else:
                return {"error": "No tool matched the intent."}
                
        except Exception as e:
            logger.error(f"Groq tool call error: {e}")
            return {"error": f"Tool routing failed: {str(e)}"}

# Singleton instance must be initialized with the API key in ws_main.py or config
model_router = None
