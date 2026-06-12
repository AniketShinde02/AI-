const { execSync } = require('child_process');
const path = require('path');

const scriptsDir = path.join(__dirname, '.planning', 'sentinel', 'scripts');

const command = process.argv[2];
const args = process.argv.slice(3).join(' ');

switch (command) {
  case 'index':
    console.log('Running Sentinel Indexing...');
    execSync(`node ${path.join(scriptsDir, 'fingerprint.js')}`, { stdio: 'inherit' });
    break;
  case 'query':
    execSync(`node ${path.join(scriptsDir, 'query.js')} ${args}`, { stdio: 'inherit' });
    break;
  case 'seed':
    execSync(`node ${path.join(scriptsDir, 'seed_summaries.js')}`, { stdio: 'inherit' });
    break;
  default:
    console.log('Sentinel CLI');
    console.log('Usage:');
    console.log('  node sentinel.js index          - Update file fingerprints');
    console.log('  node sentinel.js query <term>   - Scoped search with summaries');
    console.log('  node sentinel.js seed           - Seed core summaries');
}
