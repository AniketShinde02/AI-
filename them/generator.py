import os
import json
import re
from datetime import datetime

def scan_codebase(root_dir):
    nodes = []
    links = []
    
    # Define interesting patterns
    python_patterns = {
        'class': re.compile(r'class\s+([a-zA-Z0-9_]+)'),
        'function': re.compile(r'def\s+([a-zA-Z0-9_]+)'),
        'route': re.compile(r'@app\.(get|post|put|delete)\(["\'](.+?)["\']\)')
    }
    
    ts_patterns = {
        'interface': re.compile(r'interface\s+([a-zA-Z0-9_]+)'),
        'component': re.compile(r'export\s+const\s+([a-zA-Z0-9_]+)\s*:\s*React\.FC'),
        'trpc': re.compile(r'([a-zA-Z0-9_]+):\s*publicProcedure'),
        'hook': re.compile(r'export\s+const\s+(use[a-zA-Z0-9_]+)')
    }

    log_entries = []
    log_entries.append(f"# Codebase Scan Log - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log_entries.append("\n## System Components\n")

    for root, dirs, files in os.walk(root_dir):
        # Skip noisy dirs
        if any(x in root for x in ['node_modules', '.git', 'venv', '__pycache__', '.next']):
            continue
            
        for file in files:
            path = os.path.join(root, file)
            rel_path = os.path.relpath(path, root_dir)
            
            if file.endswith('.py') or file.endswith(('.ts', '.tsx')):
                node_id = rel_path
                nodes.append({
                    "id": node_id,
                    "label": file,
                    "group": "backend" if "backend" in rel_path else "frontend",
                    "size": os.path.getsize(path) / 100
                })
                
                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    
                    # Extract entities for logs
                    found_entities = []
                    patterns = python_patterns if file.endswith('.py') else ts_patterns
                    for key, regex in patterns.items():
                        matches = regex.findall(content)
                        for match in matches:
                            if isinstance(match, tuple):
                                match = f"{match[0]} {match[1]}"
                            found_entities.append(f"{key}: {match}")
                    
                    if found_entities:
                        log_entries.append(f"### {rel_path}")
                        for ent in found_entities:
                            log_entries.append(f"- {ent}")
                        log_entries.append("")

    # Save Graph Data
    graph_data = {"nodes": nodes, "links": links}
    with open(os.path.join(root_dir, 'them/graph.json'), 'w') as f:
        json.dump(graph_data, f, indent=2)
        
    # Save Logs
    with open(os.path.join(root_dir, 'them/logs.md'), 'w') as f:
        f.write("\n".join(log_entries))

if __name__ == "__main__":
    try:
        scan_codebase(".")
        print("[OK] Graph data and logs generated in /them folder")
    except Exception as e:
        print(f"Error: {e}")
