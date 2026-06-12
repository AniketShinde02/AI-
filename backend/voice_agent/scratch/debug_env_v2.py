import os
import json
from dotenv import load_dotenv

load_dotenv()

cred_str = os.getenv("FIREBASE_CREDENTIALS")
if not cred_str:
    print("FIREBASE_CREDENTIALS not found")
    exit(1)

# Strip potential surrounding quotes
raw_json = cred_str.strip()
if (raw_json.startswith("'") and raw_json.endswith("'")) or \
   (raw_json.startswith('"') and raw_json.endswith('"')):
    raw_json = raw_json[1:-1]

print(f"Total length: {len(raw_json)}")

# Find all backslashes and their context
for i, char in enumerate(raw_json):
    if char == '\\':
        context = raw_json[max(0, i-5):min(len(raw_json), i+6)]
        # Use repr to see exactly what characters are there
        print(f"Backslash at index {i}: repr context: {repr(context)}")
        # Check if next char is valid for JSON escape
        if i + 1 < len(raw_json):
            next_char = raw_json[i+1]
            if next_char not in ['"', '\\', '/', 'b', 'f', 'n', 'r', 't', 'u']:
                print(f"!!! INVALID JSON ESCAPE FOUND: \\{next_char} at index {i}")

try:
    json.loads(raw_json)
    print("json.loads success")
except Exception as e:
    print(f"json.loads FAILED: {e}")
