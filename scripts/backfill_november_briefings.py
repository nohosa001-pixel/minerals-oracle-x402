# -*- coding: utf-8 -*-
"""Autonomous November 2026 Historical Intelligence Backfill & Brain Consolidation
================================================================================
Checks all dates from 2026-11-01 to 2026-11-16, generates any missing market
and EUDR briefing reports via Gemini 3.8 Flash, and immediately consolidates
them into the ElizaOS Brain memory bank.
"""

from __future__ import annotations

import os
import sys
import time
import datetime
from pathlib import Path
from dotenv import load_dotenv

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
load_dotenv(PROJECT_ROOT / ".env")

from scripts.generate_daily_market_briefing import generate_market_briefing
from scripts.generate_daily_eudr_briefing import generate_eudr_briefing
from app.modules.elizaos_brain_security_bridge import ElizaOSBrainSecurityBridge


def backfill_missing_briefings():
    start_date = datetime.date(2026, 11, 1)
    end_date = datetime.date(2026, 11, 16)
    delta = datetime.timedelta(days=1)

    reports_dir = PROJECT_ROOT / "docs" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    current_date = start_date
    generated_count = 0

    print("================================================================================")
    print("  NOVEMBER 2026 INTELLIGENCE AUDIT & BACKFILL ENGINE")
    print(f"  Range: {start_date.isoformat()} ~ {end_date.isoformat()}")
    print("================================================================================")

    while current_date <= end_date:
        date_iso = current_date.isoformat()
        market_file = reports_dir / f"{date_iso}_market_briefing.md"
        eudr_file = reports_dir / f"{date_iso}_eudr_briefing.md"

        # Check Market Briefing
        if not market_file.exists():
            print(f"\n[BACKFILL] Missing Market Briefing for {date_iso}. Generating...")
            try:
                generate_market_briefing(current_date)
                generated_count += 1
                time.sleep(2)
            except Exception as exc:
                print(f"[ERROR] Failed to generate Market Briefing for {date_iso}: {exc}")
        else:
            print(f"[AUDIT] {date_iso} Market Briefing OK.")

        # Check EUDR Briefing
        if not eudr_file.exists():
            print(f"\n[BACKFILL] Missing EUDR Briefing for {date_iso}. Generating...")
            try:
                generate_eudr_briefing(current_date)
                generated_count += 1
                time.sleep(2)
            except Exception as exc:
                print(f"[ERROR] Failed to generate EUDR Briefing for {date_iso}: {exc}")
        else:
            print(f"[AUDIT] {date_iso} EUDR Briefing OK.")

        # Consolidate into ElizaOS Brain
        if market_file.exists():
            try:
                content = market_file.read_text(encoding="utf-8")[:1500]
                res = ElizaOSBrainSecurityBridge.absorb_daily_intelligence(content, date_iso)
                print(f"[BRAIN] {date_iso} consolidated into Brain memory -> {res.get('status')}")
            except Exception as exc:
                print(f"[BRAIN ERROR] Could not absorb {date_iso}: {exc}")

        current_date += delta

    print("\n================================================================================")
    print(f"  Backfill complete! Generated {generated_count} new report(s).")
    print("================================================================================")


if __name__ == "__main__":
    backfill_missing_briefings()

