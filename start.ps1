Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "  Starting Yellow.ai Agent Inbox" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan

# 1. Initialize venv if not present
if (-not (Test-Path ".venv")) {
    Write-Host "[1/3] Creating virtual environment..." -ForegroundColor Yellow
    python -m venv .venv
    .\.venv\Scripts\pip install -r requirements.txt
}

# 2. Seed database
Write-Host "[2/3] Seeding database..." -ForegroundColor Yellow
.\.venv\Scripts\python seed.py

# 3. Launch server (Serves both API and Frontend at http://127.0.0.1:8000)
Write-Host "[3/3] Launching server on http://127.0.0.1:8000 ..." -ForegroundColor Green
Write-Host "Open http://127.0.0.1:8000 in your browser." -ForegroundColor Green
.\.venv\Scripts\python -m uvicorn main:app --reload
