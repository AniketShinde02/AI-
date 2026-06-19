const fs = require('fs');
const dotenv = require('dotenv');
const path = require('path');

const envPath = path.join(__dirname, '..', 'frontend', '.env');
const envConfig = dotenv.parse(fs.readFileSync(envPath));
const creds = envConfig.FIREBASE_CREDENTIALS;

console.log("Searching for backslashes in FIREBASE_CREDENTIALS:");
let index = -1;
while ((index = creds.indexOf('\\', index + 1)) !== -1) {
  const context = creds.substring(index - 10, index + 15);
  console.log(`At index ${index}: ...${context.replace(/\n/g, '\\n')}...`);
}
