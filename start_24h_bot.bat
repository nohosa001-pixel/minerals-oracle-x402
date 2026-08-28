@echo off
chcp 65001 >nul
title Minerals Oracle x402 - 24/7 Arbitrage Trading Bot
color 0A

echo ===========================================================================
echo   💎 Minerals Oracle x402 - 24/7 Autonomous Arbitrage Agent Launcher
echo   🏦 Broker: Korea Investment & Securities (KIS 10061681-08)
echo   ⛓️ Network: Polygon Mainnet (Chain ID 137)
echo ===========================================================================
echo.
echo Starting 24/7 automated scanning loop...
echo (Press Ctrl+C anytime to stop cleanly)
echo.

python run_arbitrage_agent.py --loop

pause
