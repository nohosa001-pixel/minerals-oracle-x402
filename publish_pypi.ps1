# ========================================================
#   minerals-oracle-x402 PyPI Distribution Script
# ========================================================

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "  minerals-oracle-x402 PyPI Release Uploader" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan

# 1. Check dist files
if (-not (Test-Path "dist\minerals_oracle_x402-1.0.0-py3-none-any.whl")) {
    Write-Host "[ERROR] Distribution files not found in dist/. Please run 'python -m build' first." -ForegroundColor Red
    exit 1
}

# 2. Check twine validation
Write-Host "`n[1/3] Running twine validation..." -ForegroundColor Yellow
python -m twine check dist/*
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Twine verification failed." -ForegroundColor Red
    exit 1
}

# 3. Prompt for API Token if not set in environment
$pypiToken = $env:TWINE_PASSWORD
if ([string]::IsNullOrEmpty($pypiToken)) {
    Write-Host "`n[2/3] PyPI API Token Required" -ForegroundColor Yellow
    Write-Host "Please enter your PyPI API Token (starts with 'pypi-...'):" -ForegroundColor Gray
    $pypiToken = Read-Host -MaskInput "PyPI Token"
}

if ([string]::IsNullOrEmpty($pypiToken)) {
    Write-Host "[ERROR] PyPI Token cannot be empty." -ForegroundColor Red
    exit 1
}

# 4. Upload to PyPI
Write-Host "`n[3/3] Uploading package to PyPI (https://upload.pypi.org/legacy/)..." -ForegroundColor Yellow
$env:TWINE_USERNAME = "__token__"
$env:TWINE_PASSWORD = $pypiToken

python -m twine upload dist/*

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n========================================================" -ForegroundColor Green
    Write-Host "  [SUCCESS] Successfully published to PyPI!" -ForegroundColor Green
    Write-Host "========================================================" -ForegroundColor Green
    Write-Host "Package URL: https://pypi.org/project/minerals-oracle-x402/" -ForegroundColor Cyan
    Write-Host "Install: pip install minerals-oracle-x402" -ForegroundColor Cyan
    Write-Host "Run MCP: uvx minerals-oracle-x402" -ForegroundColor Cyan
} else {
    Write-Host "`n[ERROR] Upload failed. Please check your PyPI token and network connection." -ForegroundColor Red
}
