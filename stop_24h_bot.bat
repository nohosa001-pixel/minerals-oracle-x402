@echo off
chcp 65001 >nul
title Stop Minerals Oracle 24/7 Bot
color 0C

echo ===========================================================================
echo   🛑 Stopping Minerals Oracle 24/7 Arbitrage Agent Processes...
echo ===========================================================================
echo.

taskkill /F /FI "WINDOWTITLE eq Minerals Oracle x402 - 24/7 Arbitrage Trading Bot" /T 2>nul
wmic process where "commandline like '%%run_arbitrage_agent.py%%'" call terminate 2>nul

echo.
echo [SUCCESS] All 24/7 trading bot processes have been stopped.
echo.
pause
