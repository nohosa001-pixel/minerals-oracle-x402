@echo off
setlocal
echo ========================================================
echo   minerals-oracle-x402 v1.6.0 PyPI Release Uploader
echo ========================================================

if not exist "dist\minerals_oracle_x402-1.6.0-py3-none-any.whl" (
    echo [*] Distribution files not found in dist/. Running build...
    uv build
)

echo.
echo [1/2] Verifying package with Twine...
python -m twine check dist\minerals_oracle_x402-1.6.0*
if errorlevel 1 (
    echo [ERROR] Twine verification failed.
    pause
    exit /b 1
)

echo.
echo [2/2] Ready to upload to PyPI.
powershell -ExecutionPolicy Bypass -File publish_pypi.ps1
echo.
pause
