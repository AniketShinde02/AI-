import os
import json
from dotenv import load_dotenv

load_dotenv()

cred_str = os.getenv("FIREBASE_CREDENTIALS")
print(f"Raw string length: {len(cred_str) if cred_str else 0}")
if cred_str:
    print(f"Starts with: {cred_str[:50]}")
    # Try to find what's at char 629
    if len(cred_str) > 635:
        print(f"Context around char 629: '{cred_str[620:640]}'")
    
    try:
        # Strip potential surrounding quotes
        raw_json = cred_str.strip()
        if (raw_json.startswith("'") and raw_json.endswith("'")) or \
           (raw_json.startswith('"') and raw_json.endswith('"')):
            raw_json = raw_json[1:-1]
        
        # Manually escape backslashes if they are literal in the env
        # Actually, if it's a JSON string, backslashes MUST be escaped.
        # If the private key has \n, it should be \\n in the JSON string.
        # But if it's \n (literal), json.loads might fail if it's not a valid escape.
        
        data = json.loads(raw_json)
        print("✅ JSON parsed successfully")
    except Exception as e:
        print(f"❌ JSON parse failed: {e}")
