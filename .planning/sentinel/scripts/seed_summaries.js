const fs = require('fs');
const path = require('path');

const SENTINEL_DIR = path.resolve(__dirname, '..');
const MANIFEST_PATH = path.join(SENTINEL_DIR, 'manifest.json');

const INITIAL_SUMMARIES = {
  'backend/src/main.py': 'Main entry point for the backend FastAPI application. Orchestrates routes and services.',
  'backend/src/backend/voice/groq_llm.py': 'Custom GroqLLM implementation for voice interaction. Handles streaming completions from Groq models.',
  'backend/src/backend/voice/orchestrator.py': 'Voice session orchestrator. Manages the lifecycle of voice calls and agent interactions.',
  'frontend/src/contexts/NexusContext.tsx': 'Central React context for managing global application state, including chat, voice sessions, and API configurations.',
  'frontend/src/components/InputArea.tsx': 'Core UI component for user interaction. Supports text input, voice session toggling, and real-time visual feedback (waveform).',
  '.planning/codebase/ARCHITECTURE.md': 'System architecture documentation including high-level diagrams and component descriptions.',
  'CHANGELOG.md': 'Master record of project changes following Keep a Changelog format.'
};

function seedSummaries() {
  if (!fs.existsSync(MANIFEST_PATH)) {
    console.error('Manifest not found.');
    return;
  }

  const manifest = JSON.parse(fs.readFileSync(MANIFEST_PATH, 'utf8'));
  let updated = 0;

  for (const [filePath, summary] of Object.entries(INITIAL_SUMMARIES)) {
    // Normalize path for matching
    const normalizedKey = path.normalize(filePath);
    
    // Find matching key in manifest (ignoring case and normalization differences)
    const key = Object.keys(manifest.files).find(k => 
      path.normalize(k).toLowerCase() === normalizedKey.toLowerCase()
    );

    if (key) {
      manifest.files[key].summary = summary;
      updated++;
    } else {
      console.log(`Could not find key for: ${filePath} (tried ${normalizedKey})`);
    }
  }

  fs.writeFileSync(MANIFEST_PATH, JSON.stringify(manifest, null, 2));
  console.log(`Seeded ${updated} summaries into manifest.`);
}

seedSummaries();
