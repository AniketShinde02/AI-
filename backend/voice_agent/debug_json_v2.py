import os
from dotenv import load_dotenv
import json

load_dotenv()
creds = os.environ.get("FIREBASE_CREDENTIALS")
print(f"Type: {type(creds)}")
if creds:
    creds = creds.strip("'\"")
    try:
        data = json.loads(creds)
        print("JSON Load Success")
    except Exception as e:
        print(f"JSON Load Failed: {str(e)}")
        # context
        msg = str(e)
        if "char" in msg:
            try:
                import re
                match = re.search(r"char (\d+)", msg)
                if match:
                    idx = int(match.group(1))
                    start = max(0, idx - 10)
                    end = min(len(creds), idx + 10)
                    print(f"Context around char {idx}: '{creds[start:end]}'")
                    print(f"Char at {idx}: '{creds[idx]}'")
            except:
                pass
