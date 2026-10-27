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

    # 3. Optional A.GRID Ops Clearing Dispatch
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


def main():
    parser = argparse.ArgumentParser(description="Autonomous 24/7 Unified Intelligence Daemon")
    parser.add_argument("--time", type=str, default="09:00", help="Daily execution time (HH:MM 24h, default: 09:00)")
    parser.add_argument("--now", action="store_true", help="Force execute immediately on startup regardless of existing files")
    args = parser.parse_args()

    print("=" * 80)
    print("  MINERALS & EUDR ORACLE X402 AUTONOMOUS UNIFIED INTELLIGENCE DAEMON")
    print(f"  Target Schedule: Daily at {args.time} KST")
    print("  Engine: Google Gemini 3.8 Flash with Live Google Search Grounding")
    print("=" * 80)

    # Initial check on launch: ensure today's reports are present
    today = datetime.date.today()
    reports_dir = PROJECT_ROOT / "docs" / "reports"
    market_exists = (reports_dir / f"{today.strftime('%Y-%m-%d')}_market_briefing.md").exists()
    eudr_exists = (reports_dir / f"{today.strftime('%Y-%m-%d')}_eudr_briefing.md").exists()

    if args.now or not market_exists or not eudr_exists:
        print(f"[Startup] Today's briefings check: Market={market_exists}, EUDR={eudr_exists}. Running maintenance...")
        execute_full_daily_intelligence_cycle(today)
    else:
        print(f"[Startup] Today's briefings ({today.strftime('%Y-%m-%d')}) are already present and up to date.")

    # Register daily schedule
    schedule.every().day.at(args.time).do(execute_full_daily_intelligence_cycle)

    print(f"[Daemon] Scheduled daily run set to {args.time} KST.")
    print(f"[Daemon] Active and listening in background... (Press Ctrl+C to stop)")

    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    main()
