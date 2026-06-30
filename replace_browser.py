import os
import re

MAPPINGS = {
    'core.browser_agent': 'core.browser.facade',
}

def process_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    new_content = content
    for old, new in MAPPINGS.items():
        new_content = re.sub(r'\b' + re.escape(old) + r'\b', new, new_content)

    if new_content != content:
        print(f'Updated {filepath}')
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)

for root, dirs, files in os.walk(r'd:\AI\backend\nexus_core'):
    if 'shim_backup' in root or '__pycache__' in root:
        continue
    for file in files:
        if file.endswith('.py'):
            try:
                process_file(os.path.join(root, file))
            except Exception as e:
                pass
