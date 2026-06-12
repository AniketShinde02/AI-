const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const ROOT_DIR = path.resolve(__dirname, '../../..');
const SENTINEL_DIR = path.resolve(__dirname, '..');
const MANIFEST_PATH = path.join(SENTINEL_DIR, 'manifest.json');

const IGNORE_DIRS = [
  'node_modules',
  '.git',
  '.next',
  'dist',
  'build',
  'venv',
  '.venv',
  '__pycache__',
  '.chats',
  'graphify-out',
  '.windsurf'
];

const IGNORE_PATHS = [
  path.join('.planning', 'sentinel')
];

function getHash(filePath) {
  try {
    const fileBuffer = fs.readFileSync(filePath);
    const hashSum = crypto.createHash('sha256');
    hashSum.update(fileBuffer);
    return hashSum.digest('hex');
  } catch (e) {
    return null;
  }
}

function walkDir(dir, fileList = []) {
  try {
    const files = fs.readdirSync(dir);
    files.forEach(file => {
      const filePath = path.join(dir, file);
      try {
        const stat = fs.lstatSync(filePath);
        const relativePath = path.relative(ROOT_DIR, filePath);

        if (stat.isSymbolicLink()) return;

        if (stat.isDirectory()) {
          const isIgnoredDir = IGNORE_DIRS.includes(file);
          const isIgnoredPath = IGNORE_PATHS.some(p => relativePath.startsWith(p));
          
          if (!isIgnoredDir && !isIgnoredPath) {
            walkDir(filePath, fileList);
          }
        } else {
          fileList.push({
            path: relativePath,
            absPath: filePath,
            mtime: stat.mtimeMs
          });
        }
      } catch (e) {
        // Skip files that can't be accessed
      }
    });
  } catch (e) {
    // Skip directories that can't be accessed
  }
  return fileList;
}

function updateManifest() {
  let manifest = { files: {} };
  if (fs.existsSync(MANIFEST_PATH)) {
    manifest = JSON.parse(fs.readFileSync(MANIFEST_PATH, 'utf8'));
  }

  const allFiles = walkDir(ROOT_DIR);
  const newFiles = {};
  let changes = 0;

  allFiles.forEach(file => {
    const existing = manifest.files[file.path];
    const currentHash = getHash(file.absPath);

    if (!existing || existing.hash !== currentHash) {
      newFiles[file.path] = {
        hash: currentHash,
        lastModified: file.mtime,
        status: existing ? 'changed' : 'new',
        summary: existing ? existing.summary : null
      };
      changes++;
    } else {
      newFiles[file.path] = existing;
    }
  });

  manifest.files = newFiles;
  manifest.lastUpdate = Date.now();
  manifest.totalFiles = Object.keys(newFiles).length;

  fs.writeFileSync(MANIFEST_PATH, JSON.stringify(manifest, null, 2));
  console.log(`Manifest updated. Total files: ${manifest.totalFiles}. Changes detected: ${changes}`);
}

updateManifest();
