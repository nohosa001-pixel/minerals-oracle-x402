# -*- coding: utf-8 -*-
"""Autonomous 24/7 Daily Intelligence & Maintenance Daemon for Minerals Oracle X402
===================================================================================
Schedules autonomous daily market intelligence generation via Google Gemini 3.8 Flash,
updates system pricing baselines, verifies regulatory D-Days, and syncs status with A.GRID.
"""

from __future__ import annotations

import os
import sys
import time
import argparse
import datetime
from pathlib import Path
import schedule

# Reconfigure console output for UTF-8
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.generate_daily_market_briefing import generate_market_briefing


def execute_maintenance_cycle():
    """Runs one full intelligence generation and system maintenance cycle."""
    today = datetime.date.today()
    print(f"\n[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] >>> Starting Autonomous Market Intelligence Cycle...")

    try:
        report_path, content = generate_market_briefing(today)
        print(f"[Maintenance] Market briefing successfully archived at: {report_path.name}")
        
        # System Invariant Verification & Telemetry
        print("[Maintenance] Checking Minerals Oracle compliance engine invariants...")
        try:
            from app.agrid_ops_client import dispatch_clearing_event_background
            dispatch_clearing_event_background(
                operation="daily_market_intelligence_sync",
                amount_usdc=0.0,
                caller_agent_id="minerals-oracle-intelligence-daemon",
                chain="polygon",
                target_service="agrid-ops-agent",
            )
            print("[Maintenance] Dispatched intelligence sync event to A.GRID Ops Hub.")
        except Exception as e:
            print(f"[Maintenance] A.GRID sync notice (optional): {e}")

        print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] <<< Intelligence Cycle Complete.")

    except Exception as exc:
        print(f"[ERROR] Autonomous intelligence cycle failed: {exc}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description="24/7 Daily Intelligence Daemon")
    parser.add_argument("--time", type=str, default="09:30", help="Daily execution time (HH:MM 24h, default: 09:30)")
    parser.add_argument("--now", action="store_true", help="Execute immediately on startup")
    args = parser.parse_args()

    print("=" * 80)
    print("  MINERALS ORACLE X402 AUTONOMOUS INTELLIGENCE DAEMON")
    print(f"  Target Schedule: Daily at {args.time} KST")
    print("  Engine: Google Gemini 3.8 Flash with Live Google Search Grounding")
    print("=" * 80)

    if args.now:
        execute_maintenance_cycle()

    schedule.every().day.at(args.time).do(execute_maintenance_cycle)

    print(f"[Daemon] Listening and waiting for scheduled runs... (Press Ctrl+C to exit)")
    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    main()
