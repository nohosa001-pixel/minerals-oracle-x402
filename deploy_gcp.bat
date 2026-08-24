@echo off
setlocal
echo ========================================================
echo   minerals-oracle-x402 Google Cloud Run Deployment
echo ========================================================

:: 1. Check gcloud
where gcloud >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] gcloud CLI is not installed or not in PATH.
    pause
    exit /b 1
)

:: 2. Project config
set PROJECT_ID=my-nohosa-87175
set REGION=asia-northeast3
call gcloud config set project %PROJECT_ID%

echo Project ID: %PROJECT_ID%
echo Region: %REGION%

:: 3. Enable APIs
echo [1/2] Enabling required GCP APIs...
call gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com --quiet

:: 4. Deploy to Cloud Run
echo [2/2] Deploying container to Cloud Run...
call gcloud run deploy minerals-oracle-x402 ^
    --source . ^
    --region %REGION% ^
    --platform managed ^
    --allow-unauthenticated ^
    --memory 512Mi ^
    --cpu 1 ^
    --min-instances 0 ^
    --max-instances 10 ^
    --set-env-vars="ORACLE_TREASURY_WALLET=0x255F9991233f86B29dB847c8d5b8CB9915e80dCf,ALLOW_DEV_BYPASS=false" ^
    --quiet

if %errorlevel% equ 0 (
    echo ========================================================
    echo   [SUCCESS] Cloud Run deployment successful!
    echo ========================================================
    for /f "tokens=*" %%i in ('gcloud run services describe minerals-oracle-x402 --region %REGION% --format="value(status.url)"') do set SERVICE_URL=%%i
    echo Service URL: %SERVICE_URL%
    echo Health Check: %SERVICE_URL%/health
) else (
    echo [ERROR] Deployment failed.
)

pause
