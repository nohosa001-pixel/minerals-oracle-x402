# ========================================================
#   minerals-oracle-x402 Google Cloud Run PowerShell Script
#   (24/7 Always-On Cloud Autonomous Execution)
# ========================================================

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "  minerals-oracle-x402 24/7 Cloud Deployment" -ForegroundColor Cyan
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

# 4. Deploy to Cloud Run with 24/7 Always-On Worker settings
Write-Host "`n[2/2] Deploying 24/7 container to Cloud Run..." -ForegroundColor Yellow
gcloud run deploy minerals-oracle-x402 `
    --source . `
    --region asia-northeast3 `
    --platform managed `
    --allow-unauthenticated `
    --memory 512Mi `
    --cpu 1 `
    --min-instances 1 `
    --no-cpu-throttling `
    --max-instances 10 `
    --env-vars-file .env.yaml `
    --quiet

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n========================================================" -ForegroundColor Green
    Write-Host "  [SUCCESS] 24/7 Cloud deployment successful!" -ForegroundColor Green
    Write-Host "========================================================" -ForegroundColor Green
    $serviceUrl = (gcloud run services describe minerals-oracle-x402 --region asia-northeast3 --format="value(status.url)").Trim()
    Write-Host "Service URL: $serviceUrl" -ForegroundColor Cyan
    Write-Host "24/7 Bot Status: $serviceUrl/api/v1/bot/status" -ForegroundColor Cyan
    Write-Host "Trade History: $serviceUrl/api/v1/bot/history" -ForegroundColor Cyan
    Write-Host "Web Dashboard: $serviceUrl/dashboard" -ForegroundColor Cyan
} else {
    Write-Host "`n[ERROR] Deployment failed. Check the logs above." -ForegroundColor Red
}
