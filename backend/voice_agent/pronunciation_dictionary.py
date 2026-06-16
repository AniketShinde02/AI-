import re

PRONUNCIATION_MAP = {}

def apply_pronunciation(text: str) -> str:
    """Legacy: Hardcoded phonetics are no longer used. We now rely on native Devanagari script generation from the LLM for perfect TTS code-switching."""
    return text

def apply_speech_director(text: str) -> str:
    """
    Speech Director Layer:
    Adds pauses, emphasis, hesitation, and pacing before TTS.
    Converts literal fillers to natural pauses.
    """
    # Replace filler "Ahh" or "Hmm" with SSML-like commas/ellipses for natural pauses
    # Note: since we chunk by sentences, adding commas forces the TTS engine to pause
    
    replacements = [
        (r'\b(ahh|ah)\b', 'Ahh...'),
        (r'\b(hmm|hm)\b', 'Hmm...'),
        (r'\b(bhai)\b', 'bhai,'),
        (r'\b(arey|are)\b', 'Arey...'),
        (r'\b(so)\b', 'so...'),
        (r'\b(well)\b', 'well...'),
    ]
    
    for pattern, rep in replacements:
        text = re.sub(pattern, rep, text, flags=re.IGNORECASE)
        
    # Clean up double punctuation if created
    text = text.replace("...,", "...").replace(",.", ",").replace("....", "...")
    
    return text
