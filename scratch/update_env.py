import json
import os

json_path = r'd:\AI\backend\studio-8908067992-4e114-firebase-adminsdk-fbsvc-49d5f34889.json'
env_path = r'd:\AI\backend\nexus_core\.env'

with open(json_path, 'r') as f:
    creds = json.load(f)

minified_json = json.dumps(creds, separators=(',', ':'))

with open(env_path, 'r') as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if line.startswith('FIREBASE_CREDENTIALS='):
        new_lines.append(f"FIREBASE_CREDENTIALS='{minified_json}'\n")
    else:
        new_lines.append(line)

with open(env_path, 'w') as f:
    f.writelines(new_lines)

print("Successfully updated .env with minified Firebase credentials.")

