@echo off
setlocal
echo ========================================================
echo   minerals-oracle-x402 TypeScript SDK NPM Packager
echo ========================================================

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0publish_npm.ps1"

pause
