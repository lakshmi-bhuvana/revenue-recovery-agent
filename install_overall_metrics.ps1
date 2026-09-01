$ErrorActionPreference = "Stop"

# Run this from C:\Users\HP\revenue-recovery-agent
$root = (Get-Location).Path
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backupDir = Join-Path $root "backup\overall_metrics_$timestamp"
$zip = Join-Path $env:USERPROFILE "Downloads\overall_metrics_update.zip"
$extractDir = Join-Path $root "_overall_metrics_update"

if (-not (Test-Path $zip)) {
    throw "Could not find $zip. Download overall_metrics_update.zip first."
}

New-Item -ItemType Directory -Force -Path $backupDir | Out-Null

# Backup current files before changing anything.
Copy-Item (Join-Path $root "src\api\main.py") (Join-Path $backupDir "main.py") -Force
Copy-Item (Join-Path $root "frontend\index.html") (Join-Path $backupDir "index.html") -Force

# Clean temporary extraction directory.
if (Test-Path $extractDir) {
    Remove-Item $extractDir -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $extractDir | Out-Null

Expand-Archive -Path $zip -DestinationPath $extractDir -Force

# Install the two updated files.
Copy-Item (Join-Path $extractDir "src\api\main.py") (Join-Path $root "src\api\main.py") -Force
Copy-Item (Join-Path $extractDir "frontend\index.html") (Join-Path $root "frontend\index.html") -Force

# Validate Python syntax before starting the server.
python -m py_compile (Join-Path $root "src\api\main.py")

Write-Host ""
Write-Host "SUCCESS" -ForegroundColor Green
Write-Host "Backup: $backupDir"
Write-Host "Updated: src\api\main.py"
Write-Host "Updated: frontend\index.html"
Write-Host ""
Write-Host "Start/restart FastAPI, then open http://127.0.0.1:8000"
Write-Host "Test overall metrics with:"
Write-Host 'Invoke-RestMethod http://127.0.0.1:8000/overall-metrics | ConvertTo-Json -Depth 10'
