# Gemini Live Experiment — Quick Launcher
# Branch: nexus-gemini-live-test
# This is ISOLATED from the main Nexus backend (port 8001 vs 8000)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendVenv = "D:\AI\backend\voice_agent\venv\Scripts\python.exe"
$envFile = "D:\AI\backend\voice_agent\.env"

Write-Host ""
Write-Host "[Gemini] Starting Gemini Live Experiment..." -ForegroundColor Cyan
Write-Host "[Gemini] Branch: nexus-gemini-live-test" -ForegroundColor Gray
Write-Host "[Gemini] Port: 8001 (isolated from Nexus on 8000)" -ForegroundColor Gray
Write-Host ""

# Check GEMINI_API_KEY
if (Test-Path $envFile) {
    $envContent = Get-Content $envFile
    $hasKey = $envContent | Where-Object { $_ -match "^GEMINI_API_KEY=.+" }
    if (-not $hasKey) {
        Write-Host "[Gemini] ❌ GEMINI_API_KEY not found in .env" -ForegroundColor Red
        Write-Host "[Gemini]    Add this to D:\AI\backend\voice_agent\.env:" -ForegroundColor Yellow
        Write-Host "           GEMINI_API_KEY=your_key_here" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "    Get key at: https://aistudio.google.com/app/apikey" -ForegroundColor Cyan
        Write-Host ""
        exit 1
    }
    Write-Host "[Gemini] ✅ GEMINI_API_KEY found" -ForegroundColor Green
}

# Install google-genai if needed
Write-Host "[Gemini] Checking google-genai..." -ForegroundColor Gray
& $backendVenv -c "import google.genai" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "[Gemini] Installing google-genai..." -ForegroundColor Yellow
    & "D:\AI\backend\voice_agent\venv\Scripts\pip.exe" install google-genai fastapi uvicorn python-dotenv --quiet
}

# Open browser
Start-Process "http://localhost:8001/static/client.html"

# Run server
Write-Host "[Gemini] ✅ Starting server on http://localhost:8001" -ForegroundColor Green
Write-Host "[Gemini]    Client: http://localhost:8001/static/client.html" -ForegroundColor Cyan
Write-Host ""
Set-Location $scriptDir
& $backendVenv server.py
