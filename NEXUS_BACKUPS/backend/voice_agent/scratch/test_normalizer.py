import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, 'D:/AI/backend/voice_agent')

from text_normalizer import normalize_for_tts, detect_language

cases = [
    # Pure Hinglish
    ("Main theek hoon, dhanyavad.", "hi"),
    ("Kya aap bata sakte hain?", "hi"),
    ("Haan, bahut accha hai yeh.", "hi"),
    ("Nahi, mujhe nahi pata.", "hi"),
    # Mixed English/Hindi
    ("Open Instagram aur leads find karo.", "mixed"),
    ("Python code kaise likhte hain?", "mixed"),
    ("Mera naam Nexus hai.", "hi"),
    # Marathi
    ("Tu kasa ahes?", "mr"),
    ("Chan aahe, shukriya.", "mr"),
    # Pure English (should NOT be transliterated)
    ("Open the Instagram app.", "en"),
    ("Show me the latest leads.", "en"),
    ("How are you today?", "en"),
    # Already Devanagari (pass through)
    ("मैं ठीक हूँ।", "hi"),
]

print("=" * 70)
for text, expected_lang in cases:
    lang = detect_language(text)
    result = normalize_for_tts(text)
    changed = "✓ CHANGED" if result != text else "  same"
    lang_ok = "✓" if lang == expected_lang else f"✗ (got {lang}, expected {expected_lang})"
    print(f"[{lang_ok}] IN:  {text}")
    print(f"[{changed}] OUT: {result}")
    print()
