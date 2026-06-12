# Nexus Control Script - Windows PowerShell
$ErrorActionPreference = "Continue" # Don't stop the whole script if one process fails to kill

function Stop-ProcessOnPort($port) {
    try {
        $processId = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -First 1
        if ($processId) {
            Write-Host "[Cleanup] Killing process on port $port (PID: $processId)..." -ForegroundColor Yellow
            Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
            Start-Sleep -Seconds 1 # Wait for port to clear
        }
    } catch {
        # Port already free
    }
}

Write-Host "`n--- Nexus System Startup ---" -ForegroundColor Cyan

# 1. Cleanup existing processes to avoid "Address already in use"
Stop-ProcessOnPort 8000 # Backend
Stop-ProcessOnPort 3000 # Frontend

# 2. Select Run Mode
Write-Host "`nNexus Control Panel" -ForegroundColor Cyan
Write-Host "1. Full Stack (Frontend + Backend)"
Write-Host "2. Backend Only (Voice Server)"
Write-Host "3. Frontend Only"
Write-Host "4. Direct CLI Chat (Talk with AI Now)"
Write-Host "5. Exit"
$choice = Read-Host "`nSelect an option"

if ($choice -eq "5") { exit }

# ── 3. Start Services ───────────────────────────────────────────────────────
$backend_cmd = "cd backend/voice_agent; ..\venv\Scripts\python.exe main.py serve"
$frontend_cmd = "cd frontend; pnpm dev"
$chat_cmd = "cd backend/voice_agent; ..\venv\Scripts\python.exe chat.py"

if ($choice -eq "1") {
    Write-Host "`n🚀 Launching Full Stack..." -ForegroundColor Green
    Start-Process powershell -ArgumentList "-NoExit", "-Command", $backend_cmd
    Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontend_cmd
}
elseif ($choice -eq "2") {
    Write-Host "`n🚀 Launching Backend..." -ForegroundColor Green
    Invoke-Expression $backend_cmd
}
elseif ($choice -eq "3") {
    Write-Host "`n🚀 Launching Frontend..." -ForegroundColor Green
    Invoke-Expression $frontend_cmd
}
elseif ($choice -eq "4") {
    Write-Host "`n🚀 Launching Direct CLI Chat..." -ForegroundColor Green
    Invoke-Expression $chat_cmd
}

if ($choice -eq "1" -or $choice -eq "3") {
    $frontendPath = Join-Path $PSScriptRoot "frontend"
    # Check if pnpm exists, fallback to npm
    $manager = if (Get-Command pnpm -ErrorAction SilentlyContinue) { "pnpm" } else { "npm" }
    Write-Host "`n🚀 Starting Frontend Dev Server..." -ForegroundColor Green
    Set-Location $frontendPath
    if ($manager -eq "pnpm") {
        pnpm dev
    } else {
        npm run dev
    }
}
