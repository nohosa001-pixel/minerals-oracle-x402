# ========================================================
#   minerals-oracle-x402 v1.2.2 PyPI Distribution Script
# ========================================================

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "  minerals-oracle-x402 v1.2.2 PyPI Release Uploader" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan

# 1. Load from .env if present
if (Test-Path ".env") {
    Get-Content ".env" | ForEach-Object {
        if ($_ -match "^\s*(PYPI_API_TOKEN|TWINE_PASSWORD)\s*=\s*(.+)$") {
            $env:TWINE_PASSWORD = $matches[2].Trim().Trim('"').Trim("'")
            $env:UV_PUBLISH_TOKEN = $matches[2].Trim().Trim('"').Trim("'")
        }
    }
}

# 2. Check dist files for v1.2.2
$wheelPath = "dist\minerals_oracle_x402-1.2.2-py3-none-any.whl"
$sdistPath = "dist\minerals_oracle_x402-1.2.2.tar.gz"

if (-not (Test-Path $wheelPath) -or -not (Test-Path $sdistPath)) {
    Write-Host "[*] v1.2.2 distribution files not found. Building with uv..." -ForegroundColor Yellow
    $env:UV_LINK_MODE = "copy"
    uv build
}

# 3. Check API Token
$pypiToken = $env:TWINE_PASSWORD
if ([string]::IsNullOrEmpty($pypiToken)) {
    $pypiToken = $env:UV_PUBLISH_TOKEN
}

if ([string]::IsNullOrEmpty($pypiToken)) {
    Write-Host "`n[1/2] PyPI API Token Required" -ForegroundColor Yellow
    Write-Host "Please enter your PyPI API Token (starts with 'pypi-...'):" -ForegroundColor Gray
    $pypiToken = Read-Host -MaskInput "PyPI Token"
}

if ([string]::IsNullOrEmpty($pypiToken)) {
    Write-Host "[ERROR] PyPI Token cannot be empty." -ForegroundColor Red
    exit 1
}

# 4. Upload v1.2.2 to PyPI
Write-Host "`n[2/2] Uploading v1.2.2 package to PyPI..." -ForegroundColor Yellow
$env:UV_LINK_MODE = "copy"
$env:UV_PUBLISH_TOKEN = $pypiToken
$env:TWINE_USERNAME = "__token__"
$env:TWINE_PASSWORD = $pypiToken

# Try uv publish first on v1.2.2 files
uv publish --token $pypiToken dist/minerals_oracle_x402-1.2.2*

if ($LASTEXITCODE -ne 0) {
    Write-Host "[*] Retrying upload via twine..." -ForegroundColor Yellow
    uvx twine upload dist/minerals_oracle_x402-1.2.2* -u __token__ -p $pypiToken --skip-existing
}

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n========================================================" -ForegroundColor Green
    Write-Host "  [SUCCESS] Successfully published v1.2.2 to PyPI!" -ForegroundColor Green
    Write-Host "========================================================" -ForegroundColor Green
    Write-Host "Package URL: https://pypi.org/project/minerals-oracle-x402/1.2.2/" -ForegroundColor Cyan
    Write-Host "Install: pip install minerals-oracle-x402==1.2.2" -ForegroundColor Cyan
    Write-Host "Run MCP: uvx minerals-oracle-x402==1.2.2" -ForegroundColor Cyan
} else {
    Write-Host "`n[ERROR] Upload failed. Please check your PyPI token and permissions." -ForegroundColor Red
}
