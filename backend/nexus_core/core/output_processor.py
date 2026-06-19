import re
import logging

logger = logging.getLogger("nexus.output_processor")

class RuntimeOutputProcessor:
    """
    Global filter that strips internal reasoning, chain of thought, and planning text 
    from LLM responses before they reach the UI or TTS.
    """

    @staticmethod
    def filter_reasoning(text: str) -> str:
        if not text:
            return ""

        # 1. Strip and log <think>...</think> and <thinking>...</thinking> tags
        thinking_match = re.search(r'<(?:think|thinking|thought)>(.*?)</(?:think|thinking|thought)>', text, flags=re.DOTALL | re.IGNORECASE)
        if thinking_match:
            trace = thinking_match.group(1).strip()
            logger.info(f"🧠 [INTERNAL REASONING TRACE]:\n{trace}\n" + "-"*40)
            
        text = re.sub(r'<(?:think|thinking|thought)>.*?</(?:think|thinking|thought)>', '', text, flags=re.DOTALL | re.IGNORECASE)

        # 2. Strip *planning...*, *thinking...*, *analyzing...* 
        text = re.sub(r'\*(?:planning|thinking|analyzing|executing|searching).*?\*', '', text, flags=re.IGNORECASE | re.DOTALL)
        
        # 3. Strip conversational friction, internal reasoning, and AI disclaimers
        prefixes_to_strip = [
            r'^(?:I am|I\'m|I will|I\'ll|Let me|I need to)\s+(?:think|analyze|check|search|execute|look|find|run|open|close).*?[\.\:]\s*',
            r'^Here is the (?:information|result|answer).*?\:\s*',
            r'^Based on the (?:context|search|information).*?\:\s*',
            r'^The user wants me to.*?\.\s*',
            r'^Understood[\.\,]\s*',
            r'^Sure[\.\,\!]\s*',
            r'^Okay[\.\,\!]\s*',
            r'^As an AI(?: language model)?.*?\s*',
            r'^I have (?:executed|run|opened|closed|completed).*?[\.\:]\s*'
        ]
        
        for pattern in prefixes_to_strip:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)

        # Remove trailing explanations like "I have executed the tool" if it's the only thing left
        if re.match(r'^I have (?:executed|run|opened|closed|completed)', text, re.IGNORECASE):
            text = ""

        # 4. Clean up excessive newlines or whitespace left over from stripping
        text = re.sub(r'\n{3,}', '\n\n', text).strip()
        
        return text

output_processor = RuntimeOutputProcessor()
