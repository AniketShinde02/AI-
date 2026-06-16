Param(
    [switch]$Verbose,
    [switch]$ForceUpdate
)

$PROJECT_ROOT = $PSScriptRoot
$BACKEND_ROOT = "$PROJECT_ROOT\backend\voice_agent"
$VENV_PATH = "$PROJECT_ROOT\backend\venv"
$REQUIREMENTS = "$BACKEND_ROOT\requirements.txt"
$PYTHON_BIN = "$VENV_PATH\Scripts\python.exe"
$ENV_FILE = "$PROJECT_ROOT\backend\.env"

Write-Host "`n[Nexus] [Launch] Starting Voice Backend..." -ForegroundColor Cyan

# 1. Discover Python
$PYTHON_CMD = "python"
if (-not (Get-Command $PYTHON_CMD -ErrorAction SilentlyContinue)) {
    $PYTHON_CMD = "py"
    if (-not (Get-Command $PYTHON_CMD -ErrorAction SilentlyContinue)) {
        Write-Host "[Error] [Fatal] Python not found. Please install Python 3.10+." -ForegroundColor Red
        exit 1
    }
}

# 2. Check/Create VENV
if (-not (Test-Path $PYTHON_BIN)) {
    Write-Host "[Nexus] [Setup] Creating virtual environment in $VENV_PATH..." -ForegroundColor Yellow
    & $PYTHON_CMD -m venv $VENV_PATH
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[Error] [Fatal] Failed to create venv at $VENV_PATH." -ForegroundColor Red
        exit 1
    }
    Write-Host "[Nexus] [Success] Venv created successfully." -ForegroundColor Green
}

# 3. Sync .env to src (where settings.py expects it)
if (Test-Path $ENV_FILE) {
    Write-Host "[Nexus] [Sync] Environment check... (Using $ENV_FILE)" -ForegroundColor Gray
} else {
    Write-Host "[Warning] [Config] No .env found at $ENV_FILE." -ForegroundColor Yellow
}

# 4. Install Dependencies
Write-Host "[Nexus] [Deps] Checking dependencies..." -ForegroundColor Gray
& $PYTHON_BIN -m pip install --upgrade pip --quiet

if ($Verbose) {
    Write-Host "[Nexus] [Deps] Running pip install with full output..." -ForegroundColor Gray
    & $PYTHON_BIN -m pip install -r $REQUIREMENTS
} else {
    Write-Host "[Nexus] [Deps] Running quiet dependency check..." -ForegroundColor Gray
    & $PYTHON_BIN -m pip install -r $REQUIREMENTS --quiet
}

if ($LASTEXITCODE -ne 0) {
    Write-Host "[Error] [Fatal] Dependency check failed." -ForegroundColor Red
    exit 1
}

# 5. Start Server
Write-Host "`n[Nexus] [Server] Starting Agent Server on http://0.0.0.0:8000" -ForegroundColor Green

# Use the new Voice Agent runner
Set-Location $BACKEND_ROOT
# Set environment variables
$env:LOG_LEVEL = "INFO"
$env:PYTHONPATH = "$BACKEND_ROOT;$PROJECT_ROOT\backend"
$env:PYTHONIOENCODING = "utf-8"

# Run the Nexus Agent (Simplified WebSocket Version)
& $PYTHON_BIN -m uvicorn ws_main:app --host 0.0.0.0 --port 8001 --ws wsproto --log-level info --reload



