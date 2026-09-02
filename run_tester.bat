@echo off
chcp 65001 >nul
echo ========================================================
echo   Minerals Oracle x402 - Interactive Live Tester
echo ========================================================
set PYTHON_EXEC=python
if exist ".venv\Scripts\python.exe" (
    set PYTHON_EXEC=.venv\Scripts\python.exe
)
%PYTHON_EXEC% test_interactive.py
pause
