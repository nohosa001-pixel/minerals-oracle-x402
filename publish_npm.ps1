# ========================================================
#   minerals-oracle-x402 TypeScript SDK NPM Distribution
#   Mirrored from security-gate-x402 publishing pipeline
# ========================================================

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "  NPM Release Packager - Minerals Oracle x402 SDK       " -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan

$sdkDir = Join-Path $PSScriptRoot "sdk\typescript"
Push-Location $sdkDir

try {
    # 1. Load NPM_TOKEN from .env if present
    $envFile = Join-Path $PSScriptRoot ".env"
    if (Test-Path $envFile) {
        Get-Content $envFile | ForEach-Object {
            if ($_ -match "^\s*NPM_TOKEN\s*=\s*(.+)$") {
                $env:NODE_AUTH_TOKEN = $matches[1].Trim().Trim('"').Trim("'")
                Write-Host "[*] Loaded NPM_TOKEN from .env" -ForegroundColor Gray
            }
        }
    }

    # 2. Check dependencies
    if (-not (Test-Path "node_modules")) {
        Write-Host "[1/4] Installing SDK dependencies..." -ForegroundColor Yellow
        npm install
        if ($LASTEXITCODE -ne 0) {
            Write-Host "[ERROR] npm install failed!" -ForegroundColor Red
            exit 1
        }
    }

    # 3. Build bundle and TypeScript declarations with tsup
    Write-Host "[2/4] Building bundle and TypeScript declarations (tsup)..." -ForegroundColor Yellow
    npm run build
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Build failed!" -ForegroundColor Red
        exit 1
    }

    # 4. Run SDK unit tests
    Write-Host "[3/4] Running SDK unit tests..." -ForegroundColor Yellow
    npm test
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Tests failed!" -ForegroundColor Red
        exit 1
    }

    # 5. Inspect package metadata
    Write-Host "[4/4] Verifying npm registry status..." -ForegroundColor Yellow
    $pkgJson = Get-Content "package.json" -Raw | ConvertFrom-Json
    $pkgName = $pkgJson.name
    $pkgVersion = $pkgJson.version

    Write-Host "Package: $pkgName @ v$pkgVersion" -ForegroundColor Cyan
    $existing = npm view "$pkgName@$pkgVersion" version 2>$null
    if ($existing -eq $pkgVersion) {
        Write-Host "[WARNING] $pkgName@$pkgVersion is already published on npm registry!" -ForegroundColor Yellow
        Write-Host "To release a new version, bump 'version' in sdk/typescript/package.json." -ForegroundColor Yellow
    }

    $confirm = Read-Host "Proceed with npm publish? (y/n)"
    if ($confirm -eq "y" -or $confirm -eq "Y") {
        Write-Host "Executing npm publish --access public..." -ForegroundColor Yellow
        npm publish --access public
        if ($LASTEXITCODE -eq 0) {
            Write-Host "`n========================================================" -ForegroundColor Green
            Write-Host "  [SUCCESS] Successfully published $pkgName@$pkgVersion to npm!" -ForegroundColor Green
            Write-Host "========================================================" -ForegroundColor Green
            Write-Host "Package URL: https://www.npmjs.com/package/$pkgName" -ForegroundColor Cyan
            Write-Host "Install:     npm install $pkgName@$pkgVersion" -ForegroundColor Cyan
        } else {
            Write-Host "`n[INFO] If publish failed due to 2FA / OTP, run:" -ForegroundColor Yellow
            Write-Host "       npm publish --access public --otp=YOUR_6DIGIT_CODE" -ForegroundColor Cyan
        }
    } else {
        Write-Host "[INFO] Publish cancelled." -ForegroundColor Yellow
    }
} finally {
    Pop-Location
}
