#!/usr/bin/env pwsh
# Context Automation Script for AntiGravity
# Updates the Code Review Graph and Wiki context for the AI Agent

Write-Host "--- AntiGravity Context Sync ---" -ForegroundColor Cyan

# 1. Update/Build the Graph
Write-Host "[1/6] Updating Code Review Graph..." -ForegroundColor Yellow
python -m code_review_graph update

# 2. Generate the Wiki (Context for AI)
Write-Host "[2/6] Generating Codebase Wiki..." -ForegroundColor Yellow
python -m code_review_graph wiki --force

# 3. Generate tRPC API Documentation
Write-Host "[3/6] Extracting tRPC API Docs..." -ForegroundColor Yellow
node scripts/extract-trpc-docs.js

# 4. Build Boneyard Skeletons
if (Test-Path "frontend") {
    Write-Host "[4/6] Building Boneyard-JS bones..." -ForegroundColor Yellow
    cd frontend
    # Running build silently to keep output clean
    npx boneyard-js build | Out-Null
    cd ..
}

# 5. Cleanup Legacy Context
if (Test-Path "graphify-out") {
    Write-Host "[5/6] Removing legacy Graphify artifacts..." -ForegroundColor Yellow
    Remove-Item -Recurse -Force "graphify-out"
}

# 6. Generate Agent Summary
Write-Host "[6/6] Updating CONTEXT_SUMMARY.md..." -ForegroundColor Yellow
$date = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$summary = @"
# 🧠 Codebase Intelligence Summary
**Last Sync:** $date
**Engine:** code-review-graph + custom triggers

## 📍 Quick Entry Points
- [Wiki Index](./.code-review-graph/wiki/index.md)
- [tRPC API Docs](./.planning/codebase/TRPC_API.md)
- [Boneyard Guidelines](./BONEYARD_GUIDELINES.md)
- [Architecture](./.planning/codebase/ARCHITECTURE.md)

## 🛠️ Instructions for AI Agents
1. **Sync First**: Always run `./sync-context.ps1` after major changes.
2. **Wiki First**: Read the wiki in `.code-review-graph/wiki/` for architecture.
3. **API First**: Read `TRPC_API.md` before modifying frontend/backend contracts.
4. **Boneyard Standard**: Ensure all new UI features use `boneyard-js` skeletons.
"@

$summary | Out-File -FilePath "CONTEXT_SUMMARY.md" -Encoding utf8

Write-Host "--- Sync Complete. Agent context is now up-to-date. ---" -ForegroundColor Cyan
