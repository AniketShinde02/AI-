"""
text_normalizer.py — Pre-TTS Indian language normalization layer

Pipeline:
  LLM output → normalize_for_tts() → Piper synthesis

Goal: convert colloquial Hinglish / Roman Marathi tokens to Devanagari
before feeding to hi_IN Piper models. Hindi TTS voices are trained on
Devanagari; romanized input causes broken phonemization.

Strategy:
  1. Token-by-token processing (preserves word order, punctuation)
  2. Dictionary lookup first (covers colloquial spellings that ITRANS can't)
  3. Already-Devanagari tokens pass through unchanged
  4. Unknown tokens that look like English (brand names, tech terms) pass through
  5. ITRANS fallback only for structured academic transliteration

Scope: Hindi + Hinglish + Marathi Roman. English preserved.
"""

import re
import logging

logger = logging.getLogger("nexus.tts.normalizer")

# ─────────────────────────────────────────────────────────────────────────────
# HINGLISH / ROMAN-MARATHI → DEVANAGARI DICTIONARY
# Covers the ~250 most common spoken words. Colloquial spellings.
# Multiple spelling variants included (e.g. "nahi", "nahin", "nahi").
# ─────────────────────────────────────────────────────────────────────────────
HINGLISH_DICT: dict[str, str] = {
    # ── Pronouns ──────────────────────────────────────────────────────────
    "main": "मैं",  "mein": "मैं",   "mai": "मैं",
    "hum":  "हम",   "aap":  "आप",    "ap": "आप",
    "tum":  "तुम",  "tu":   "तू",
    "woh":  "वो",   "wo":   "वो",    "voh": "वो",
    "yeh":  "यह",   "ye":   "यह",    "yeh": "यह",
    "iska": "इसका", "uska": "उसका",  "inki": "इनकी",
    "mera": "मेरा", "meri": "मेरी",  "mere": "मेरे",
    "tera": "तेरा", "teri": "तेरी",  "tere": "तेरे",
    "aapka":"आपका", "aapki":"आपकी",  "aapke":"आपके",
    "hamara":"हमारा","hamari":"हमारी","hamare":"हमारे",
    "unka": "उनका", "unki": "उनकी",  "unke": "उनके",

    # ── To-be verbs ───────────────────────────────────────────────────────
    "hai":  "है",   "hain": "हैं",   "tha":  "था",
    "thi":  "थी",   "hoga": "होगा",
    # NOTE: 'the' REMOVED — collides with English 'the'
    "hogi": "होगी", "honge":"होंगे",
    "hoon": "हूँ",  "hun":  "हूँ",   "hoo":  "हूँ",
    "ho":   "हो",   "hua":  "हुआ",   "hui":  "हुई",
    "hue":  "हुए",  "hona": "होना",  "hoke": "होकर",

    # ── Common verbs ──────────────────────────────────────────────────────
    "kar":    "कर",    "karo":   "करो",   "karna": "करना",
    "kiya":   "किया",  "ki":     "की",    "kijiye":"कीजिए",
    "bolo":   "बोलो",  "bolta":  "बोलता", "bolti": "बोलती",
    "aata":   "आता",   "aati":   "आती",   "aao":   "आओ",
    "jao":    "जाओ",   "ja":     "जा",    "jana":  "जाना",
    "jata":   "जाता",  "jati":   "जाती",  "jaega": "जाएगा",
    "dena":   "देना",  "diya":   "दिया",   "denge":  "देंगे",
    # NOTE: 'do', 'de', 'lo' REMOVED — collide with English 'do', 'de', 'lo'
    "raha":   "रहा",   "rahi":   "रही",   "rahe":  "रहे",
    "rahega": "रहेगा", "rehna":  "रहना",
    "sakta":  "सकता",  "sakti":  "सकती",  "sakte": "सकते",
    "chahiye":"चाहिए", "chahie": "चाहिए",
    "milega": "मिलेगा","milegi": "मिलेगी","mile":  "मिले",
    "dekho":  "देखो",  "dekha":  "देखा",  "dekhna":"देखना",
    "suno":   "सुनो",  "suna":   "सुना",  "sunna": "सुनना",
    "samjho": "समझो",  "samjha": "समझा",  "samajh":"समझ",
    "puchho": "पूछो",  "poocho": "पूछो",  "pooch": "पूछ",
    "batao":  "बताओ",  "bata":   "बता",   "batana":"बताना",
    "khao":   "खाओ",   "khana":  "खाना",  "khaana":"खाना",
    "peena":  "पीना",  "piyo":   "पियो",
    "socho":  "सोचो",  "socha":  "सोचा",  "sochna":"सोचना",
    "chal":   "चल",    "chalo":  "चलो",   "chalte":"चलते",
    "ruko":   "रुको",  "ruk":    "रुक",
    "likho":  "लिखो",  "likha":  "लिखा",  "likhna":"लिखना",

    # ── Question words ────────────────────────────────────────────────────
    "kya":    "क्या",  "kab":    "कब",    "kahan": "कहाँ",
    "kahaan": "कहाँ",  "kyun":   "क्यों", "kyunki":"क्योंकि",
    "kyuki":  "क्योंकि",
    "kaise":  "कैसे",  "kitna":  "कितना", "kitni": "कितनी",
    "kitne":  "कितने", "kaun":   "कौन",   "kon":   "कौन",
    "koun":   "कौन",   "konsa":  "कौनसा", "kaisa": "कैसा",

    # ── Adjectives / Adverbs ──────────────────────────────────────────────
    "theek":  "ठीक",   "thik":   "ठीक",
    "accha":  "अच्छा", "acha":   "अच्छा", "achha": "अच्छा",
    "acchi":  "अच्छी", "achi":   "अच्छी",
    "achhe":  "अच्छे",
    "bahut":  "बहुत",  "bahot":  "बहुत",
    "bilkul": "बिल्कुल",
    "zyada":  "ज़्यादा","jyada":  "ज़्यादा",
    "thoda":  "थोड़ा", "thodi":  "थोड़ी", "thode": "थोड़े",
    "sahi":   "सही",   "galat":  "गलत",
    "naya":   "नया",   "nayi":   "नई",    "purana":"पुराना",
    "bada":   "बड़ा",  "badi":   "बड़ी",  "bade":  "बड़े",
    "chota":  "छोटा",  "choti":  "छोटी",
    "sundar": "सुंदर", "khubsurat":"खूबसूरत",
    "mushkil":"मुश्किल","aasaan":"आसान",  "asan":  "आसान",
    "bekar":  "बेकार", "bekaar": "बेकार",
    "kharab": "खराब",
    "puura":  "पूरा",  "poora":  "पूरा",  "sara":  "सारा",
    "sabhi":  "सभी",   "sab":    "सब",
    "sirf":   "सिर्फ", "bas":    "बस",
    "zaroor": "ज़रूर", "zaruri": "ज़रूरी",
    "seedha": "सीधा",  "ulta":   "उल्टा",
    "zyada":  "ज़्यादा","kam":    "कम",

    "aur":    "और",
    # NOTE: 'ya', 'hi', 'to', 'na' REMOVED — collide with English words
    "mein":   "में",   "se":     "से",    "ko":    "को",
    "par":    "पर",    "pe":     "पे",
    "bhi":    "भी",
    "toh":    "तो",
    "nahi":   "नहीं",  "nahin":  "नहीं",
    "mat":    "मत",
    "haan":   "हाँ",   "han":    "हाँ",
    "agar":   "अगर",   "lekin":  "लेकिन", "magar": "मगर",
    "phir":   "फिर",   "fir":    "फिर",
    "ab":     "अब",    "abhi":   "अभी",
    "waise":  "वैसे",  "vaise":  "वैसे",
    "matlab": "मतलब",  "yani":   "यानी",
    "isliye": "इसलिए", "kyonki": "क्योंकि",
    "jabki":  "जबकि",  "jab":    "जब",
    "tab":    "तब",    "toh":    "तो",
    "kyunki": "क्योंकि",
    "warna":  "वरना",  "nahi to":"नहीं तो",
    "pehle":  "पहले",  "baad":   "बाद",   "baadmein":"बाद में",
    "upar":   "ऊपर",   "neeche": "नीचे",  "andar": "अंदर",
    "bahar":  "बाहर",  "paas":   "पास",   "dur":   "दूर",
    "sath":   "साथ",   "saath":  "साथ",   "bina":  "बिना",
    "liye":   "लिए",   "tak":    "तक",    "ke":    "के",
    "ka":     "का",    "ki":     "की",

    # ── Time ──────────────────────────────────────────────────────────────
    "kal":    "कल",    "aaj":    "आज",    "parso": "परसों",
    "abhi":   "अभी",   "jaldi":  "जल्दी", "dhire": "धीरे",
    "hamesha":"हमेशा", "kabhi":  "कभी",   "aksar": "अक्सर",

    # ── Common nouns ──────────────────────────────────────────────────────
    "baat":   "बात",   "kaam":   "काम",   "din":   "दिन",
    "raat":   "रात",   "ghar":   "घर",    "desh":  "देश",
    "log":    "लोग",   "samay":  "समय",   "waqt":  "वक़्त",
    "paisa":  "पैसा",  "paise":  "पैसे",
    "khana":  "खाना",  "khaana": "खाना",  "pani":  "पानी",
    "chai":   "चाय",   "doodh":  "दूध",
    "naam":   "नाम",   "kaam":   "काम",   "kaam":  "काम",
    "dost":   "दोस्त", "yaar":   "यार",   "bhai":  "भाई",
    "behen":  "बहन",   "maa":    "माँ",   "baap":  "बाप",
    "beta":   "बेटा",  "beti":   "बेटी",
    "shaher": "शहर",   "gaon":   "गाँव",  "raasta":"रास्ता",
    "duniya": "दुनिया","zindagi":"ज़िंदगी",
    "cheez":  "चीज़",  "jagah":  "जगह",   "taraf": "तरफ",

    # ── Greetings / Responses ─────────────────────────────────────────────
    "namaste":   "नमस्ते",
    "namaskar":  "नमस्कार",
    "dhanyavad": "धन्यवाद",
    "shukriya":  "शुक्रिया",
    "alvida":    "अलविदा",
    "sorry":     "sorry",      # Keep English as-is
    "please":    "please",
    "hello":     "hello",

    # ── Marathi-specific ──────────────────────────────────────────────────
    "kasa":    "कसा",   "kashi":  "कशी",   "kase":  "कसे",
    "ahes":    "आहेस",  "aahe":   "आहे",   "ahe":   "आहे",
    "naahi":   "नाही",  # Marathi नाही (different from Hindi नहीं)
    "mala":    "मला",   "tula":   "तुला",  "amhala":"आम्हाला",
    "kay":     "काय",   "kuthe":  "कुठे",  "kiti":  "किती",
    "chan":    "छान",   "mast":   "मस्त",
    # NOTE: 'me' REMOVED — collides with English 'me'
    "amhi":   "आम्ही", "tumhi": "तुम्ही",
    "tyala":   "त्याला","tila":   "तिला",
    "majha":   "माझा",  "majhi":  "माझी",  "maze":  "माझे",
    "tuza":    "तुझा",  "tuzi":   "तुझी",
    "aapla":   "आपला",  "aapli":  "आपली",
    "khup":    "खूप",   "thoda":  "थोडा",
    "bara":    "बरा",   "bari":   "बरी",
    "nako":    "नको",   "hoy":    "होय",
    "yeto":    "येतो",  "yete":   "येते",  "ya":    "या",
    "jato":    "जातो",  "jate":   "जाते",
    "sangto":  "सांगतो","sangte": "सांगते",
    "bagho":   "बघो",   "bagha":  "बघा",
    "samaj":   "समज",   "aahe ka":"आहे का",

    # ── Numbers (spoken) ──────────────────────────────────────────────────
    "ek":     "एक",    "teen":   "तीन",   "char":  "चार",
    "paanch": "पाँच",  "chhe":   "छह",    "chhah": "छह",
    "saat":   "सात",   "aath":   "आठ",    "nau":   "नौ",
    "das":    "दस",    "bees":   "बीस",   "pachas":"पचास",
    "sau":    "सौ",    "hazaar": "हज़ार",

    # ── Filler / Discourse markers ────────────────────────────────────────
    "matlab": "मतलब",  "suniye": "सुनिए", "dekho":  "देखो",
    "arre":   "अरे",   "are":    "अरे",   "aho":    "अहो",
    "wah":    "वाह",   "shabash":"शाबाश",
    "chalo":  "चलो",   "theek hai":"ठीक है",
    "haan theek":"हाँ ठीक",
}

# ─────────────────────────────────────────────────────────────────────────────
# Regex helpers
# ─────────────────────────────────────────────────────────────────────────────

# Matches Devanagari block — already correct script, pass through
_RE_DEVANAGARI = re.compile(r'[\u0900-\u097F]')

# Words that are likely English brand/tech/proper nouns — don't transliterate
# Heuristic: all-caps, or contains digits, or CamelCase, or in a known skip list
_ENGLISH_PRESERVATIONS = {
    "ai", "api", "url", "http", "https", "www", "app",
    "instagram", "youtube", "whatsapp", "telegram", "google",
    "amazon", "netflix", "facebook", "twitter", "linkedin",
    "github", "python", "java", "html", "css", "sql",
    "email", "sms", "otp", "upi", "gst", "pdf", "jpg", "png",
    "call", "chat", "share", "post", "like", "send", "save",
    "open", "close", "start", "stop", "show", "hide", "check",
    "create", "update", "delete", "search", "find", "get", "set",
    "yes", "no", "ok", "okay",
}

# Punctuation that should travel with the token
_RE_WORD_SPLIT = re.compile(r'(\w+|[^\w\s]|\s+)', re.UNICODE)


def _is_devanagari(token: str) -> bool:
    return bool(_RE_DEVANAGARI.search(token))


def _has_devanagari(text: str) -> bool:
    return bool(_RE_DEVANAGARI.search(text))


def _is_english_preserve(word: str) -> bool:
    lower = word.lower()
    if lower in _ENGLISH_PRESERVATIONS:
        return True
    # All-caps (likely acronym)
    if word.isupper() and len(word) > 1:
        return True
    # Contains digits
    if any(c.isdigit() for c in word):
        return True
    return False


def _count_hinglish_tokens(tokens: list[str]) -> int:
    """Count how many tokens are recognized Hinglish words."""
    count = 0
    for tok in tokens:
        clean = tok.lower().strip(".,!?;:'\"")
        if clean in HINGLISH_DICT:
            count += 1
    return count


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def normalize_for_tts(text: str) -> str:
    """
    Normalize Indian-language text before Piper synthesis.

    Rules:
      - Already Devanagari → pass through unchanged
      - Pure English sentences (< 2 Hinglish tokens) → pass through unchanged
      - Hinglish / Roman Marathi tokens → convert to Devanagari via dictionary
      - Unknown tokens that look like English brand/tech words → preserve as-is
      - Unknown tokens that look like Roman Hindi not in dict → preserve as-is
        (better to send unknown English to Piper than garbled Devanagari)

    Returns the processed text ready for Piper synthesis.
    """
    if not text or not text.strip():
        return text

    # Fast path: already fully Devanagari
    if _has_devanagari(text):
        # Mixed: may still have roman Hinglish tokens interspersed
        # Process word by word
        return _normalize_mixed(text)

    # Split text into word tokens
    words = text.split()

    # Threshold: if fewer than 2 tokens are in HINGLISH_DICT, treat as English
    hinglish_count = _count_hinglish_tokens(words)
    # Threshold: 3+ recognized Hinglish tokens required to trigger transliteration.
    # Prevents accidental conversion of English sentences with short ambiguous words.
    if hinglish_count < 3:
        return text  # Pure English — send as-is

    # It's Hinglish — convert token by token
    result = _normalize_mixed(text)
    logger.debug(f"[Normalizer] '{text[:60]}' → '{result[:60]}'")
    return result


def _normalize_mixed(text: str) -> str:
    """
    Process text word-by-word. Handles both pure Hinglish and mixed
    Devanagari+Roman sentences.
    """
    # Tokenize preserving whitespace and punctuation
    parts = _RE_WORD_SPLIT.findall(text)
    output = []

    for part in parts:
        # Whitespace — preserve exactly
        if part.isspace():
            output.append(part)
            continue

        # Punctuation — preserve
        if not any(c.isalnum() for c in part):
            output.append(part)
            continue

        # Already Devanagari — pass through
        if _is_devanagari(part):
            output.append(part)
            continue

        # Strip surrounding punctuation for lookup
        stripped = part.lower().strip(".,!?;:'\"()[]")

        # Dictionary lookup (handles all colloquial variants)
        if stripped in HINGLISH_DICT:
            replacement = HINGLISH_DICT[stripped]
            # Re-apply trailing punctuation
            punct_suffix = part[len(part.rstrip(".,!?;:'\"()[]")):]
            output.append(replacement + punct_suffix)
            continue

        # Multi-word phrase lookup (e.g. "theek hai" as one entry)
        # Already handled at token level — single words only here

        # English preservation
        if _is_english_preserve(part):
            output.append(part)
            continue

        # Unknown token — keep as-is rather than risk broken ITRANS
        output.append(part)

    return "".join(output)


def detect_language(text: str) -> str:
    """
    Lightweight language tag for logging/debugging.
    Returns: 'hi' | 'mr' | 'en' | 'mixed'
    """
    if not text:
        return "en"

    if _has_devanagari(text):
        return "hi"  # Could be mr, but close enough for TTS purposes

    words = text.lower().split()
    hinglish_hits = sum(1 for w in words if w.strip(".,!?") in HINGLISH_DICT)

    if hinglish_hits == 0:
        return "en"
    if hinglish_hits / max(len(words), 1) > 0.5:
        return "hi"
    return "mixed"
