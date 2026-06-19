const fs = require('fs');
const path = require('path');

const jsonPath = path.join(__dirname, '..', 'backend', 'studio-8908067992-4e114-firebase-adminsdk-fbsvc-49d5f34889.json');
const originalData = JSON.parse(fs.readFileSync(jsonPath, 'utf8'));

const minified = JSON.stringify(originalData);
console.log("Minified length:", minified.length);
console.log("Minified snippet:", minified.substring(0, 150));

// Let's compare minified with what is currently in frontend/.env
const envPath = path.join(__dirname, '..', 'frontend', '.env');
const dotenv = require('dotenv');
const envConfig = dotenv.parse(fs.readFileSync(envPath));
const credsInEnv = envConfig.FIREBASE_CREDENTIALS;

console.log("Creds in env length:", credsInEnv ? credsInEnv.length : 0);

if (credsInEnv === minified) {
  console.log("SUCCESS! They are identical.");
} else {
  console.log("DIFFERENT!");
  // Find the first index of difference
  let diffIdx = -1;
  const maxLen = Math.max(minified.length, credsInEnv.length);
  for (let i = 0; i < maxLen; i++) {
    if (minified[i] !== credsInEnv[i]) {
      diffIdx = i;
      break;
    }
  }
  console.log(`Difference starts at index ${diffIdx}:`);
  console.log(`Minified: ...${minified.substring(diffIdx - 10, diffIdx + 30).replace(/\n/g, '\\n')}...`);
  console.log(`Env:      ...${credsInEnv.substring(diffIdx - 10, diffIdx + 30).replace(/\n/g, '\\n')}...`);
}
