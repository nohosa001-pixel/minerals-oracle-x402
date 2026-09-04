@echo off
chcp 65001 >nul
title Minerals Oracle x402 - 24/7 Arbitrage Trading Bot
color 0A

echo ===========================================================================
echo   💎 Minerals Oracle x402 - 24/7 Autonomous Arbitrage Agent
echo   🏦 Broker: Korea Investment & Securities (KIS 10061681-08)
echo   ⛓️ Network: Polygon Mainnet (Chain ID 137)
echo   🔔 Telegram Alerts: Enabled
echo ===========================================================================
echo.
echo [INFO] Starting 24/7 automated scanning loop...
echo (You can minimize this window. Press Ctrl+C anytime to stop cleanly.)
echo.

cd /d "%~dp0"

set PYTHON_EXEC=python
if exist ".venv\Scripts\python.exe" (
    set PYTHON_EXEC=.venv\Scripts\python.exe
)

:LOOP_START
%PYTHON_EXEC% -u run_arbitrage_agent.py --loop

echo.
echo [WARN] Bot process ended. Restarting in 5 seconds...
timeout /t 5 >nul
goto LOOP_START
