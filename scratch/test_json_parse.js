const fs = require('fs');
const dotenv = require('dotenv');
const path = require('path');

// Load the .env file
const envPath = path.join(__dirname, '..', 'frontend', '.env');
const envConfig = dotenv.parse(fs.readFileSync(envPath));

const credentialsString = envConfig.FIREBASE_CREDENTIALS;
console.log("Raw credentials length:", credentialsString ? credentialsString.length : 0);

try {
  const parsed = JSON.parse(credentialsString);
  console.log("Success! Parsed without correction.");
} catch (e) {
  console.log("Failed to parse raw string:", e.message);
  
  // Apply our regex correction
  const corrected = credentialsString.replace(/\\(?!["\\/bfnrtu])/g, '\\n');
  
  try {
    const parsedCorrected = JSON.parse(corrected);
    console.log("Success with correction! Project ID:", parsedCorrected.project_id);
    console.log("Private Key snippet:", parsedCorrected.private_key.substring(0, 100));
  } catch (err) {
    console.log("Failed even with correction:", err.message);
  }
}
