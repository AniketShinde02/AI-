import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from indic_transliteration import sanscript as sc
from indic_transliteration.sanscript import transliterate

words = ["main", "theek", "hoon", "kya", "aur", "nahi", "haan", "kaise", "bahut", "accha", "dhanyavad", "namaste"]
print("ITRANS -> Devanagari:")
for w in words:
    r = transliterate(w, sc.ITRANS, sc.DEVANAGARI)
    print(f"  {w:15} -> {r}")
