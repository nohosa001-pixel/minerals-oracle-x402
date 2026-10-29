# -*- coding: utf-8 -*-
"""Autonomous 24/7 Unified Daily Intelligence & Compliance Daemon for Minerals & EUDR Oracle
=============================================================================================
Combines:
1. Daily Global Critical Minerals & Precious Metals Market Intelligence Generator
2. Daily EUDR Regulatory & Supply Chain Intelligence Generator

Features:
- On startup, automatically verifies if today's briefings exist in `docs/reports/`.
  If missing, immediately generates them so no day is missed.
- Schedules automated daily generation every morning (default: 09:00 KST).
- Dispatches background sync telemetry to A.GRID Ops Hub.
- Supports Telegram alerts if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are configured.
"""

from __future__ import annotations

import os
import sys
import time
import argparse
import datetime
from pathlib import Path
import schedule
from dotenv import load_dotenv

# Reconfigure console output for UTF-8
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
load_dotenv(PROJECT_ROOT / ".env")

from scripts.generate_daily_market_briefing import generate_market_briefing
from scripts.generate_daily_eudr_briefing import generate_eudr_briefing
from scripts.dispatch_telegram_daily_briefing import dispatch_daily_reports_to_telegram


def send_telegram_alert(summary_text: str):
    """Sends a summary alert via Telegram bot if configured in environment."""
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    enabled = os.getenv("TELEGRAM_NOTIFICATIONS_ENABLED", "false").lower() in ("true", "1", "yes")

    if not enabled or not bot_token or not chat_id:
        return

    try:
        from app.modules.notification_manager import NotificationManager
        NotificationManager.send_telegram_message(
            text=summary_text,
            bot_token=bot_token,
            chat_id=chat_id,
            force_live=True,
        )
        print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] [Telegram] Summary alert successfully sent.")
    except Exception as exc:
        print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] [Telegram] Alert skipped: {exc}")


def execute_full_daily_intelligence_cycle(target_date: Optional[datetime.date] = None):
    """Executes both market briefing and EUDR regulatory briefing generation."""
    if target_date is None:
        target_date = datetime.date.today()

    iso_date = target_date.strftime("%Y-%m-%d")
    print(f"\n{'='*75}")
    print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] >>> Starting Unified Intelligence Cycle for {iso_date}")
    print(f"{'='*75}")

    reports_dir = PROJECT_ROOT / "docs" / "reports"
    market_report_path = reports_dir / f"{iso_date}_market_briefing.md"
    eudr_report_path = reports_dir / f"{iso_date}_eudr_briefing.md"

    # 1. Market Briefing
    if not market_report_path.exists():
        print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] [Market] Generating daily market briefing...")
        try:
            m_path, m_content = generate_market_briefing(target_date)
            print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] [Market] Successfully saved {m_path.name}")
        except Exception as exc:
            print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] [ERROR] Market briefing failed: {exc}", file=sys.stderr)
    else:
        print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] [Market] Report already exists: {market_report_path.name}")

    # 2. EUDR Briefing
    if not eudr_report_path.exists():
        print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] [EUDR] Generating daily EUDR regulatory briefing...")
        try:
            e_path, e_content = generate_eudr_briefing(target_date)
            print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] [EUDR] Successfully saved {e_path.name}")
        except Exception as exc:
            print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] [ERROR] EUDR briefing failed: {exc}", file=sys.stderr)
    else:
        print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] [EUDR] Report already exists: {eudr_report_path.name}")

    # 3. Automatic Telegram Delivery
    try:
        dispatch_daily_reports_to_telegram(target_date)
    except Exception as exc:
        print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] [Telegram] Dispatch notice: {exc}")

    # 4. Optional A.GRID Ops Clearing Dispatch
    try:
        from app.agrid_ops_client import dispatch_clearing_event_background
        dispatch_clearing_event_background(
            operation="daily_unified_intelligence_sync",
            amount_usdc=0.0,
            caller_agent_id="minerals-oracle-unified-daemon",
            chain="polygon",
            target_service="agrid-ops-agent",
        )
        print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] [A.GRID] Telemetry dispatched to A.GRID Ops Hub.")
    except Exception:
        pass

    print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] <<< Unified Intelligence Cycle Complete for {iso_date}.\n")


import ctypes


def disable_windows_quick_edit():
    """Disables QuickEdit mode in Windows console to prevent accidental click freeze."""
    if os.name != "nt":
        return
    try:
        kernel32 = ctypes.windll.kernel32
        h_stdin = kernel32.GetStdHandle(-10)  # STD_INPUT_HANDLE = -10
        mode = ctypes.c_uint32()
        if kernel32.GetConsoleMode(h_stdin, ctypes.byref(mode)):
            ENABLE_QUICK_EDIT_MODE = 0x0040
            new_mode = mode.value & ~ENABLE_QUICK_EDIT_MODE
            kernel32.SetConsoleMode(h_stdin, new_mode)
    except Exception:
        pass


def catchup_missing_briefings(days_back: int = 2, force_now: bool = False):
    """Scans past N days and today; automatically generates any missing reports."""
    today = datetime.date.today()
    reports_dir = PROJECT_ROOT / "docs" / "reports"
    for d in range(days_back, -1, -1):
        target_date = today - datetime.timedelta(days=d)
        iso_date = target_date.strftime("%Y-%m-%d")
        market_file = reports_dir / f"{iso_date}_market_briefing.md"
        eudr_file = reports_dir / f"{iso_date}_eudr_briefing.md"
        if force_now or not market_file.exists() or not eudr_file.exists():
            print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] [Catch-up] Missing briefing(s) for {iso_date}. Generating...", flush=True)
            try:
                execute_full_daily_intelligence_cycle(target_date)
            except Exception as exc:
                print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] [ERROR] Cycle failed for {iso_date}: {exc}", file=sys.stderr, flush=True)
        else:
            print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] [Audit] {iso_date} briefings verified present.", flush=True)


def main():
    disable_windows_quick_edit()

    parser = argparse.ArgumentParser(description="Autonomous 24/7 Unified Intelligence Daemon")
    parser.add_argument("--time", type=str, default="09:00", help="Daily execution time (HH:MM 24h, default: 09:00)")
    parser.add_argument("--now", action="store_true", help="Force execute immediately on startup regardless of existing files")
    parser.add_argument("--catchup-days", type=int, default=2, help="Number of past days to check for missing reports (default: 2)")
    args = parser.parse_args()

    print("=" * 80, flush=True)
    print("  MINERALS & EUDR ORACLE X402 AUTONOMOUS UNIFIED INTELLIGENCE DAEMON", flush=True)
    print(f"  Target Schedule: Daily at {args.time} KST", flush=True)
    print(f"  Catch-up Window: Past {args.catchup_days} days", flush=True)
    print("  Engine: Google Gemini 3.8 Flash with Live Google Search Grounding", flush=True)
    print("=" * 80, flush=True)

    # Initial retrospective audit on launch
    catchup_missing_briefings(days_back=args.catchup_days, force_now=args.now)

    # Register daily schedule
    schedule.every().day.at(args.time).do(execute_full_daily_intelligence_cycle)

    print(f"[Daemon] Scheduled daily run set to {args.time} KST.", flush=True)
    print(f"[Daemon] Active and listening in background with anti-freeze protection... (Press Ctrl+C to stop)", flush=True)

    last_catchup_check = time.time()
    while True:
        schedule.run_pending()

        # Periodic audit every 30 minutes in case system woke from sleep/hibernate
        if time.time() - last_catchup_check > 1800:
            last_catchup_check = time.time()
            catchup_missing_briefings(days_back=1)

        time.sleep(30)


if __name__ == "__main__":
    main()

