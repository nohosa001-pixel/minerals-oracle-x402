@echo off
chcp 65001 > nul
title Minerals Oracle X402 Autonomous Intelligence Daemon

echo =====================================================================
echo  Starting Minerals Oracle & EUDR 24/7 Autonomous Intelligence Daemon
echo =====================================================================
echo.

python "%~dp0scripts\run_daily_unified_daemon.py" --time 09:00

pause
