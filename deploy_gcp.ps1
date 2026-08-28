# ========================================================
#   minerals-oracle-x402 Google Cloud Run PowerShell Script
# ========================================================

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "  minerals-oracle-x402 Cloud Run Deployment" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan

# 1. Check gcloud CLI
if (-not (Get-Command gcloud -ErrorAction SilentlyContinue)) {
    Write-Host "[ERROR] gcloud CLI is not installed or not in PATH." -ForegroundColor Red
    exit 1
}

# 2. Get current GCP Project
$currentProject = (gcloud config get-value project 2>$null).Trim()
if ([string]::IsNullOrEmpty($currentProject)) {
    $currentProject = "my-nohosa-87175"
    gcloud config set project $currentProject
}

Write-Host "Project ID: $currentProject" -ForegroundColor Green
Write-Host "Region: asia-northeast3 (Seoul)" -ForegroundColor Green

# 3. Enable APIs
Write-Host "`n[1/2] Enabling required GCP APIs (run, cloudbuild, artifactregistry)..." -ForegroundColor Yellow
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com --quiet

# 4. Deploy to Cloud Run
Write-Host "`n[2/2] Deploying container to Cloud Run..." -ForegroundColor Yellow
gcloud run deploy minerals-oracle-x402 `
    --source . `
    --region asia-northeast3 `
    --platform managed `
    --allow-unauthenticated `
    --memory 512Mi `
    --cpu 1 `
    --min-instances 0 `
    --max-instances 10 `
    --set-env-vars="ORACLE_TREASURY_WALLET=0x255F9991233f86B29dB847c8d5b8CB9915e80dCf,ALLOW_DEV_BYPASS=false,POLYGON_CHAIN_ID=137,CHAIN_ID=137,DEFAULT_PRICE_USDC=0.005,X402_FACILITATOR_URL=https://facilitator.polygon.technology/v1/verify" `
    --quiet

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n========================================================" -ForegroundColor Green
    Write-Host "  [SUCCESS] Cloud Run deployment successful!" -ForegroundColor Green
    Write-Host "========================================================" -ForegroundColor Green
    $serviceUrl = (gcloud run services describe minerals-oracle-x402 --region asia-northeast3 --format="value(status.url)").Trim()
    Write-Host "Service URL: $serviceUrl" -ForegroundColor Cyan
    Write-Host "Health Check: $serviceUrl/health" -ForegroundColor Cyan
    Write-Host "Alpha Signals: $serviceUrl/api/v1/oracle/alpha-signals" -ForegroundColor Cyan
    Write-Host "AP2 Manifest: $serviceUrl/.well-known/ap2" -ForegroundColor Cyan
} else {
    Write-Host "`n[ERROR] Deployment failed. Check the logs above." -ForegroundColor Red
}
