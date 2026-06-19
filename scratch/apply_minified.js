const fs = require('fs');
const path = require('path');

const jsonPath = path.join(__dirname, '..', 'backend', 'studio-8908067992-4e114-firebase-adminsdk-fbsvc-49d5f34889.json');
const originalData = JSON.parse(fs.readFileSync(jsonPath, 'utf8'));
const minified = JSON.stringify(originalData);

const envPaths = [
  path.join(__dirname, '..', 'frontend', '.env'),
  path.join(__dirname, '..', 'backend', '.env')
];

envPaths.forEach(envPath => {
  if (fs.existsSync(envPath)) {
    let content = fs.readFileSync(envPath, 'utf8');
    // Replace the FIREBASE_CREDENTIALS line
    const regex = /^FIREBASE_CREDENTIALS=.*$/m;
    if (regex.test(content)) {
      content = content.replace(regex, `FIREBASE_CREDENTIALS='${minified}'`);
      fs.writeFileSync(envPath, content, 'utf8');
      console.log(`Successfully repaired credentials in: ${envPath}`);
    } else {
      console.log(`FIREBASE_CREDENTIALS line not found in: ${envPath}`);
    }
  } else {
    console.log(`Env file does not exist: ${envPath}`);
  }
});
