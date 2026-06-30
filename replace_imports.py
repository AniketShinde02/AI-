import os
import re

MAPPINGS = {
    'core.action_router': 'core.planner.action_router',
    'core.agent_swarm': 'core.orchestrator.swarm',
    'core.app_discovery': 'core.desktop.discovery',
    'core.capabilities': 'core.orchestrator.capabilities',
    'core.capability_registry_def': 'core.orchestrator.registry_def',
    'core.gemini_live_manager': 'core.voice.live_manager',
    'core.guardrails': 'core.verification.guardrails',
    'core.lance_memory': 'core.memory.vector_store',
    'core.model_router': 'core.provider.router',
    'core.output_contract': 'core.planner.contract',
    'core.output_processor': 'core.planner.processor',
    'core.pc_control': 'core.desktop.control',
    'core.provider_governor': 'core.provider.governor',
    'core.rag_oracle': 'core.memory.rag_engine',
    'core.scrapper_os': 'core.vision.ocr_scraper',
    'core.session_state': 'core.workspace.state',
    'core.session_tts_worker': 'core.voice.tts_worker',
    'core.task_cards': 'core.workspace.ux_cards',
    'core.verification_matrix': 'core.verification.matrix',
    'core.vision_parser': 'core.vision.parser',
    'core.voice_session': 'core.voice.session'
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
    if 'shim_backup' in root:
        continue
    for file in files:
        if file.endswith('.py'):
            process_file(os.path.join(root, file))
