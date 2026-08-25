@echo off
setlocal
echo ========================================================
echo   minerals-oracle-x402 PyPI Release Uploader
echo ========================================================

if not exist "dist\minerals_oracle_x402-1.0.0-py3-none-any.whl" (
    echo [ERROR] Distribution files not found in dist/. Running build...
    python -m build
)

echo.
echo [1/2] Verifying package with Twine...
python -m twine check dist/*
if errorlevel 1 (
    echo [ERROR] Twine verification failed.
    pause
    exit /b 1
)

echo.
echo [2/2] Ready to upload to PyPI.
echo Run the following command with your PyPI token:
echo python -m twine upload dist/* -u __token__ -p ^<YOUR_PYPI_API_TOKEN^>
echo.
pause
