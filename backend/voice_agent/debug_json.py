import os
from dotenv import load_dotenv
import json

load_dotenv()
creds = os.environ.get("FIREBASE_CREDENTIALS")
print(f"Type: {type(creds)}")
print(f"Length: {len(creds) if creds else 0}")
if creds:
    creds = creds.strip("'\"")
    try:
        data = json.loads(creds)
        print("✅ JSON Load Success")
    except Exception as e:
        print(f"❌ JSON Load Failed: {e}")
        # Try to find character 629
        if "char 629" in str(e) or "column 630" in str(e):
            start = max(0, 620)
            end = min(len(creds), 640)
            print(f"Context around char 629: '{creds[start:end]}'")
            print(f"Char at 629: '{creds[629]}'")
