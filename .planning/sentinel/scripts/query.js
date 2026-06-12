const fs = require('fs');
const path = require('path');

const SENTINEL_DIR = path.resolve(__dirname, '..');
const MANIFEST_PATH = path.join(SENTINEL_DIR, 'manifest.json');

function query(searchTerm, limit = 5) {
  if (!fs.existsSync(MANIFEST_PATH)) {
    console.error('Manifest not found. Run fingerprint.js first.');
    return;
  }

  const manifest = JSON.parse(fs.readFileSync(MANIFEST_PATH, 'utf8'));
  const files = manifest.files;

  // Simple keyword matching for now
  const matches = Object.keys(files)
    .map(filePath => ({
      path: filePath,
      score: filePath.toLowerCase().includes(searchTerm.toLowerCase()) ? 10 : 0,
      summary: files[filePath].summary
    }))
    .filter(match => match.score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, limit);

  const visited = new Set();
  let totalEstimatedTokens = 0;
  const TOKEN_BUDGET = 8000;

  console.log(`\n--- Sentinel Query Results for "${searchTerm}" ---`);
  
  matches.forEach(m => {
    if (visited.has(m.path)) return;
    visited.add(m.path);

    const summary = m.summary || 'No summary available.';
    const estimatedTokens = Math.ceil(summary.length / 4);

    if (totalEstimatedTokens + estimatedTokens > TOKEN_BUDGET) {
      console.log(`[${m.path}] - SKIPPED (Token budget exceeded)`);
      return;
    }

    totalEstimatedTokens += estimatedTokens;
    console.log(`[${m.path}]`);
    console.log(`Summary: ${summary}`);
    console.log('---');
  });

  console.log(`\nTotal Estimated Tokens for summaries: ${totalEstimatedTokens} / ${TOKEN_BUDGET}`);

  if (matches.length === 0) {
    console.log('No matches found.');
  }
}

const args = process.argv.slice(2);
if (args.length === 0) {
  console.log('Usage: node query.js <searchTerm> [limit]');
} else {
  query(args[0], args[1] ? parseInt(args[1]) : 5);
}
