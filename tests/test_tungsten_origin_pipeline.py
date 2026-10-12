"""
Comprehensive Test Suite for Tungsten (Ammonium Paratungstate / Concentrate) Provenance Pipeline.
Validates:
1. Canonical Western Tungsten Tenements (Sangdong KOR, Cantung CAN, Panasqueira PRT, IMA Project USA).
2. ASTM B783 / ISO 10386 APT Grade Standards (WO3 >= 88.50%).
3. OECD Annex II & Dodd-Frank Section 1502 3TG Conflict-Free Certification.
4. US NDAA Section 848 Defense Procurement Non-Covered Nation Eligibility.
5. Out-of-bounds Geofence Rejection & Nearest Centroid Fallback.
6. REST API Endpoints (/api/v1/oracle/verify/tungsten & /api/v1/tungsten/verify-origin).
7. MCP Tool Integration via stdio dispatcher.
"""

import json
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas import (
    TungstenOriginVerifyRequest,
    SourceCountry,
)
from app.tungsten_pipeline import tungsten_pipeline
from app.mcp_stdio import handle_tools_list, handle_tool_call

client = TestClient(app)


def test_sangdong_korea_canonical_mine_provenance():
    """Verify Almonty Korea Sangdong mine in Gangwon-do (World's largest Western deposit)."""
    req = TungstenOriginVerifyRequest(
        batch_id="W-SANGDONG-2026-001",
        tenement_id="SANGDONG",
        latitude=37.150,
        longitude=128.833,
        apt_wo3_grade_pct=89.4,
        dodd_frank_conflict_free=True,
        ndaa_defense_procurement_eligible=True,
        source_country=SourceCountry.KOR,
    )
    res = tungsten_pipeline.verify_tungsten_batch(req)

    assert res.status == "success"
    assert res.batch_id == "W-SANGDONG-2026-001"
    assert res.audit_verdict.is_compliant is True
    assert res.audit_verdict.status == "COMPLIANT_CERTIFIED"
    assert res.audit_verdict.geofence_verified is True
    assert res.audit_verdict.distance_to_concession_km == 0.0
    assert res.audit_verdict.apt_grade_certified is True
    assert res.audit_verdict.dodd_frank_passed is True
    assert res.audit_verdict.ndaa_defense_eligible is True
    assert res.audit_verdict.confidence_score >= 0.95
    assert any("Almonty Korea Sangdong Tungsten Mine" in r for r in res.audit_verdict.reasons)
    assert any("US Department of Defense procurement under NDAA Section 848" in r for r in res.audit_verdict.reasons)
    assert res.proof_hash.startswith("0x")
    assert res.onchain_signature.startswith("0x")
    assert res.signed_by.startswith("0x")


def test_cantung_canada_mine_provenance():
    """Verify NATC Cantung Tungsten Mine in Northwest Territories, Canada."""
    req = TungstenOriginVerifyRequest(
        batch_id="W-CANTUNG-2026-002",
        tenement_id="CANTUNG",
        latitude=61.960,  # ~1.2 km offset from centroid (61.954, -128.243)
        longitude=-128.250,
        apt_wo3_grade_pct=88.75,
        dodd_frank_conflict_free=True,
        ndaa_defense_procurement_eligible=True,
        source_country=SourceCountry.CAN,
    )
    res = tungsten_pipeline.verify_tungsten_batch(req)

    assert res.status == "success"
    assert res.audit_verdict.is_compliant is True
    assert res.audit_verdict.geofence_verified is True
    assert res.audit_verdict.distance_to_concession_km < 25.0
    assert res.audit_verdict.apt_grade_certified is True
    assert res.audit_verdict.ndaa_defense_eligible is True


def test_panasqueira_portugal_mine_provenance():
    """Verify Beralt Panasqueira Wolframite underground mine in Portugal."""
    req = TungstenOriginVerifyRequest(
        batch_id="W-PANASQUEIRA-2026-003",
        tenement_id="PANASQUEIRA",
        latitude=40.158,
        longitude=-7.747,
        apt_wo3_grade_pct=88.9,
        dodd_frank_conflict_free=True,
        ndaa_defense_procurement_eligible=True,
        source_country=SourceCountry.PRT,
    )
    res = tungsten_pipeline.verify_tungsten_batch(req)

    assert res.status == "success"
    assert res.audit_verdict.is_compliant is True
    assert res.audit_verdict.geofence_verified is True
    assert res.audit_verdict.apt_grade_certified is True


def test_ima_project_usa_mine_provenance():
    """Verify American Tungsten IMA Project in Idaho, USA."""
    req = TungstenOriginVerifyRequest(
        batch_id="W-IMA-2026-004",
        tenement_id="IMA_PROJECT",
        latitude=44.492,
        longitude=-113.882,
        apt_wo3_grade_pct=89.1,
        dodd_frank_conflict_free=True,
        ndaa_defense_procurement_eligible=True,
        source_country=SourceCountry.USA,
    )
    res = tungsten_pipeline.verify_tungsten_batch(req)

    assert res.status == "success"
    assert res.audit_verdict.is_compliant is True
    assert res.audit_verdict.geofence_verified is True
    assert res.audit_verdict.ndaa_defense_eligible is True


def test_sub_grade_apt_wo3_rejection():
    """Reject Tungsten batch when WO3 purity is below ASTM standard (88.50%)."""
    req = TungstenOriginVerifyRequest(
        batch_id="W-LOWGRADE-005",
        tenement_id="SANGDONG",
        latitude=37.150,
        longitude=128.833,
        apt_wo3_grade_pct=86.20,  # Below 88.50%
        dodd_frank_conflict_free=True,
        ndaa_defense_procurement_eligible=True,
        source_country=SourceCountry.KOR,
    )
    res = tungsten_pipeline.verify_tungsten_batch(req)

    assert res.audit_verdict.is_compliant is False
    assert res.audit_verdict.status == "NON_COMPLIANT_REJECTED"
    assert res.audit_verdict.apt_grade_certified is False
    assert any("below standard grade (88.50%)" in r for r in res.audit_verdict.reasons)


def test_conflict_3tg_contamination_rejection():
    """Reject Tungsten batch flagged with 3TG conflict mining contamination."""
    req = TungstenOriginVerifyRequest(
        batch_id="W-CONFLICT-006",
        tenement_id="PANASQUEIRA",
        latitude=40.158,
        longitude=-7.747,
        apt_wo3_grade_pct=89.0,
        dodd_frank_conflict_free=False,  # Conflict contamination
        ndaa_defense_procurement_eligible=True,
        source_country=SourceCountry.PRT,
    )
    res = tungsten_pipeline.verify_tungsten_batch(req)

    assert res.audit_verdict.is_compliant is False
    assert res.audit_verdict.status == "NON_COMPLIANT_REJECTED"
    assert res.audit_verdict.dodd_frank_passed is False
    assert any("conflict 3TG contamination" in r for r in res.audit_verdict.reasons)


def test_out_of_bounds_geofence_rejection():
    """Reject extraction coordinates far outside registered tenement perimeter."""
    req = TungstenOriginVerifyRequest(
        batch_id="W-OOB-007",
        tenement_id="SANGDONG",
        latitude=35.100,  # >200 km away from Sangdong (37.150, 128.833)
        longitude=129.000,
        apt_wo3_grade_pct=89.0,
        dodd_frank_conflict_free=True,
        ndaa_defense_procurement_eligible=True,
        source_country=SourceCountry.KOR,
    )
    res = tungsten_pipeline.verify_tungsten_batch(req)

    assert res.audit_verdict.is_compliant is False
    assert res.audit_verdict.geofence_verified is False
    assert any("deviate" in r for r in res.audit_verdict.reasons)


def test_ndaa_defense_ineligibility_flag():
    """Flag ineligibility when batch does not meet US DoD NDAA Sec 848 defense criteria."""
    req = TungstenOriginVerifyRequest(
        batch_id="W-NON-DEFENSE-008",
        tenement_id="IMA_PROJECT",
        latitude=44.492,
        longitude=-113.882,
        apt_wo3_grade_pct=88.8,
        dodd_frank_conflict_free=True,
        ndaa_defense_procurement_eligible=False,  # Ineligible for defense
        source_country=SourceCountry.USA,
    )
    res = tungsten_pipeline.verify_tungsten_batch(req)

    assert res.audit_verdict.ndaa_defense_eligible is False
    assert any("Ineligible for US DoD military hardware procurement" in r for r in res.audit_verdict.reasons)


def test_nearest_concession_fallback_matching():
    """Ensure pipeline matches nearest registered concession when tenement_id is unlisted."""
    req = TungstenOriginVerifyRequest(
        batch_id="W-NEARBY-009",
        tenement_id="UNLISTED_PROSPECT",
        latitude=37.155,  # ~0.6 km from Sangdong centroid (37.150, 128.833)
        longitude=128.835,
        apt_wo3_grade_pct=89.2,
        dodd_frank_conflict_free=True,
        ndaa_defense_procurement_eligible=True,
        source_country=SourceCountry.KOR,
    )
    res = tungsten_pipeline.verify_tungsten_batch(req)

    assert res.audit_verdict.is_compliant is True
    assert res.audit_verdict.geofence_verified is True
    assert any("Tungsten centroid geofenced near Almonty Korea Sangdong" in r for r in res.audit_verdict.reasons)


def test_api_verify_tungsten_endpoints():
    """Validate REST endpoints: /api/v1/oracle/verify/tungsten and /api/v1/tungsten/verify-origin."""
    payload = {
        "batch_id": "W-API-TEST-001",
        "tenement_id": "SANGDONG",
        "latitude": 37.150,
        "longitude": 128.833,
        "apt_wo3_grade_pct": 89.5,
        "dodd_frank_conflict_free": True,
        "ndaa_defense_procurement_eligible": True,
        "source_country": "KOR"
    }

    # 1. Verification with dev bypass header
    resp1 = client.post(
        "/api/v1/oracle/verify/tungsten",
        json=payload,
        headers={"X-Dev-Bypass": "true"}
    )
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert data1["status"] == "success"
    assert data1["audit_verdict"]["is_compliant"] is True
    assert data1["audit_verdict"]["geofence_verified"] is True
    assert data1["onchain_signature"] is not None

    # 2. Dual endpoint /api/v1/tungsten/verify-origin
    resp2 = client.post(
        "/api/v1/tungsten/verify-origin",
        json=payload,
        headers={"X-Dev-Bypass": "true"}
    )
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["status"] == "success"
    assert data2["audit_verdict"]["apt_grade_certified"] is True


def test_mcp_stdio_verify_tungsten_origin_tool():
    """Verify verify_tungsten_origin tool registration and execution in MCP stdio handler."""
    # 1. Tools list contains verify_tungsten_origin
    tools_list = handle_tools_list("req_tungsten_list")
    tool_names = [t["name"] for t in tools_list["result"]["tools"]]
    assert "verify_tungsten_origin" in tool_names

    # 2. Execute tool call via stdio
    call_res = handle_tool_call(
        "req_tungsten_call",
        "verify_tungsten_origin",
        {
            "batch_id": "W-MCP-001",
            "tenement_id": "PANASQUEIRA",
            "latitude": 40.158,
            "longitude": -7.747,
            "apt_wo3_grade_pct": 89.0,
            "dodd_frank_conflict_free": True,
            "ndaa_defense_procurement_eligible": True,
            "source_country": "PRT"
        }
    )
    assert "result" in call_res
    content = json.loads(call_res["result"]["content"][0]["text"])
    assert content["status"] == "success"
    assert content["audit_verdict"]["is_compliant"] is True
    assert content["audit_verdict"]["geofence_verified"] is True
    assert content["audit_verdict"]["ndaa_defense_eligible"] is True
