"""
Tests for 2026-10-28 and 2026-10-29 Market & EUDR Regulatory Intelligence,
TypeScript SDK Parity, and Provenance Extensions.
"""

from pathlib import Path
import pytest
from app.schemas import MineralType, SourceCountry


def test_schema_expanded_minerals_and_countries():
    """Verify that newly added minerals and countries in schema exist and normalize aliases correctly."""
    assert MineralType.INDIUM_INGOT == "INDIUM_INGOT"
    assert MineralType("INDIUM") == MineralType.INDIUM_INGOT
    assert MineralType("GA") == MineralType.GALLIUM_METAL
    assert MineralType("YTTRIUM") == MineralType.YTTRIUM_OXIDE
    assert MineralType("ALUMINIUM") == MineralType.ALUMINIUM_INGOT

    assert SourceCountry.JPN == "JPN"
    assert SourceCountry("JAPAN") == SourceCountry.JPN
    assert SourceCountry.AUT == "AUT"
    assert SourceCountry("AUSTRIA") == SourceCountry.AUT
    assert SourceCountry.TJK == "TJK"
    assert SourceCountry("TAJIKISTAN") == SourceCountry.TJK
    assert SourceCountry.UZB == "UZB"
    assert SourceCountry.GIN == "GIN"


def test_oct28_reports_integrity():
    """Verify that 2026-10-28 market and EUDR briefings exist and contain mandatory sections."""
    root = Path(__file__).resolve().parent.parent
    market_file = root / "docs" / "reports" / "2026-10-28_market_briefing.md"
    eudr_file = root / "docs" / "reports" / "2026-10-28_eudr_briefing.md"

    assert market_file.exists(), "2026-10-28_market_briefing.md must exist"
    assert eudr_file.exists(), "2026-10-28_eudr_briefing.md must exist"

    market_content = market_file.read_text(encoding="utf-8")
    assert "2026-10-28" in market_content
    assert "구리 (Copper)" in market_content
    assert "은 (Silver)" in market_content
    assert "금 (Gold)" in market_content

    eudr_content = eudr_file.read_text(encoding="utf-8")
    assert "2026-10-28" in eudr_content
    assert "EUDR" in eudr_content
    assert "TRACES NT" in eudr_content


def test_oct29_reports_integrity():
    """Verify that 2026-10-29 market and EUDR briefings exist and contain mandatory sections."""
    root = Path(__file__).resolve().parent.parent
    market_file = root / "docs" / "reports" / "2026-10-29_market_briefing.md"
    eudr_file = root / "docs" / "reports" / "2026-10-29_eudr_briefing.md"

    assert market_file.exists(), "2026-10-29_market_briefing.md must exist"
    assert eudr_file.exists(), "2026-10-29_eudr_briefing.md must exist"

    market_content = market_file.read_text(encoding="utf-8")
    assert "2026-10-29" in market_content
    assert "구리 (Copper)" in market_content
    assert "은 (Silver)" in market_content
    assert "금 (Gold)" in market_content

    eudr_content = eudr_file.read_text(encoding="utf-8")
    assert "2026-10-29" in eudr_content
    assert "EUDR" in eudr_content
    assert "TRACES NT" in eudr_content
