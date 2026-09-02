@echo off
chcp 65001 >nul
title Deploy minerals-oracle-x402 to Google Cloud Run (24/7 Always-On)
color 0B

echo ===========================================================================
echo   🚀 Minerals Oracle x402 - Google Cloud Run 24/7 Deployment
echo   Region: asia-northeast3 (Seoul)
echo ===========================================================================
echo.

powershell -ExecutionPolicy Bypass -File deploy_gcp.ps1

echo.
pause
