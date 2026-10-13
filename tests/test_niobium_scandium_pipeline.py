"""
Tests for Niobium & Scandium Defense Strategic Materials Provenance Pipeline.
Validates:
1. NioCorp Elk Creek (Nebraska, USA) Ferroniobium & Scandium Oxide provenance.
2. CBMM Araxá (Brazil) & Niobec (Canada) Allied Niobium geofencing.
3. ASTM A550 (FeNb >= 65.0%) and Aerospace Sc2O3 (>= 99.5%) assay standards.
4. US NDAA Section 848 defense eligibility and US DOE & EXIM pre-qualification.
5. REST API endpoints and FastMCP tool execution.
"""

import json
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas import (
    NiobiumScandiumOriginVerifyRequest,
    MineralType,
    SourceCountry,
)
from app.niobium_scandium_pipeline import niobium_scandium_pipeline
from app.mcp_stdio import handle_tools_list, handle_tool_call

client = TestClient(app)


def test_elk_creek_ferroniobium_geofence_and_defense_certified():
    """Verify NioCorp Elk Creek Project Ferroniobium batch in Nebraska, USA."""
    req = NiobiumScandiumOriginVerifyRequest(
        batch_id="NB-ELK-2026-001",
        tenement_id="ELK_CREEK",
        latitude=40.274,
        longitude=-96.183,
        commodity_type=MineralType.FERRONIOBIUM,
        fe_nb_grade_pct=66.8,  # Meets ASTM A550 (>= 65.0%)
        doe_exim_loan_eligible=True,
        ndaa_defense_procurement_eligible=True,
        source_country=SourceCountry.USA,
    )
    res = niobium_scandium_pipeline.verify_origin(req)

    assert res.status == "success"
    assert res.audit_verdict.is_compliant is True
    assert res.audit_verdict.status == "COMPLIANT_CERTIFIED"
    assert res.audit_verdict.geofence_verified is True
    assert res.audit_verdict.distance_to_concession_km == 0.0
    assert res.audit_verdict.grade_assay_certified is True
    assert res.audit_verdict.defense_procurement_eligible is True
    assert res.audit_verdict.doe_exim_loan_eligible is True
    assert res.audit_verdict.confidence_score >= 95.0
    assert res.onchain_signature is not None and res.onchain_signature.startswith("0x")


def test_elk_creek_scandium_oxide_aerospace_certified():
    """Verify NioCorp Elk Creek Scandium Oxide batch meeting aerospace grade."""
    req = NiobiumScandiumOriginVerifyRequest(
        batch_id="SC-ELK-2026-002",
        tenement_id="ELK_CREEK",
        latitude=40.274,
        longitude=-96.183,
        commodity_type=MineralType.SCANDIUM_OXIDE,
        sc2o3_purity_pct=99.75,  # Meets Aerospace standard (>= 99.50%)
        doe_exim_loan_eligible=True,
        ndaa_defense_procurement_eligible=True,
        source_country=SourceCountry.USA,
    )
    res = niobium_scandium_pipeline.verify_origin(req)

    assert res.status == "success"
    assert res.audit_verdict.is_compliant is True
    assert res.audit_verdict.geofence_verified is True
    assert res.audit_verdict.grade_assay_certified is True
    assert any("Scandium Oxide purity" in r and "aerospace" in r for r in res.audit_verdict.reasons)


def test_araxa_brazil_ferroniobium():
    """Verify CBMM Araxá Niobium complex in Minas Gerais, Brazil."""
    req = NiobiumScandiumOriginVerifyRequest(
        batch_id="NB-ARAXA-2026-003",
        tenement_id="ARAXA",
        latitude=-19.645,
        longitude=-46.940,
        commodity_type=MineralType.FERRONIOBIUM,
        fe_nb_grade_pct=65.5,
        doe_exim_loan_eligible=False,
        ndaa_defense_procurement_eligible=True,
        source_country=SourceCountry.BRA,
    )
    res = niobium_scandium_pipeline.verify_origin(req)

    assert res.status == "success"
    assert res.audit_verdict.is_compliant is True
    assert res.audit_verdict.geofence_verified is True
    assert res.audit_verdict.distance_to_concession_km == 0.0
    assert res.audit_verdict.grade_assay_certified is True


def test_sub_grade_ferroniobium_rejection():
    """Reject Ferroniobium when Nb content is below ASTM A550 standard (65.0%)."""
    req = NiobiumScandiumOriginVerifyRequest(
        batch_id="NB-LOW-004",
        tenement_id="ELK_CREEK",
        latitude=40.274,
        longitude=-96.183,
        commodity_type=MineralType.FERRONIOBIUM,
        fe_nb_grade_pct=61.5,  # Below 65.0%
        doe_exim_loan_eligible=True,
        ndaa_defense_procurement_eligible=True,
        source_country=SourceCountry.USA,
    )
    res = niobium_scandium_pipeline.verify_origin(req)

    assert res.audit_verdict.is_compliant is False
    assert res.audit_verdict.status == "NON_COMPLIANT_REJECTED"
    assert res.audit_verdict.grade_assay_certified is False
    assert any("below ASTM A550 standard grade" in r for r in res.audit_verdict.reasons)


def test_sub_grade_scandium_oxide_rejection():
    """Reject Scandium Oxide when purity is below 99.50%."""
    req = NiobiumScandiumOriginVerifyRequest(
        batch_id="SC-LOW-005",
        tenement_id="ELK_CREEK",
        latitude=40.274,
        longitude=-96.183,
        commodity_type=MineralType.SCANDIUM_OXIDE,
        sc2o3_purity_pct=98.8,  # Below 99.50%
        doe_exim_loan_eligible=True,
        ndaa_defense_procurement_eligible=True,
        source_country=SourceCountry.USA,
    )
    res = niobium_scandium_pipeline.verify_origin(req)

    assert res.audit_verdict.is_compliant is False
    assert res.audit_verdict.grade_assay_certified is False
    assert any("below aerospace specification standard" in r for r in res.audit_verdict.reasons)


def test_out_of_bounds_geofence_rejection():
    """Reject extraction coordinates far outside registered tenement perimeter."""
    req = NiobiumScandiumOriginVerifyRequest(
        batch_id="NB-OOB-006",
        tenement_id="ELK_CREEK",
        latitude=35.100,  # Far away from Nebraska (40.274, -96.183)
        longitude=-90.000,
        commodity_type=MineralType.FERRONIOBIUM,
        fe_nb_grade_pct=66.0,
        doe_exim_loan_eligible=True,
        ndaa_defense_procurement_eligible=True,
        source_country=SourceCountry.USA,
    )
    res = niobium_scandium_pipeline.verify_origin(req)

    assert res.audit_verdict.is_compliant is False
    assert res.audit_verdict.geofence_verified is False
    assert any("deviate" in r for r in res.audit_verdict.reasons)


def test_rest_api_verify_niobium_scandium_origin():
    """Verify REST endpoint /api/v1/oracle/verify/niobium-scandium and /api/v1/niobium-scandium/verify-origin."""
    payload = {
        "batch_id": "NB-API-001",
        "tenement_id": "ELK_CREEK",
        "latitude": 40.274,
        "longitude": -96.183,
        "commodity_type": "FERRONIOBIUM",
        "fe_nb_grade_pct": 66.5,
        "doe_exim_loan_eligible": True,
        "ndaa_defense_procurement_eligible": True,
        "source_country": "USA",
    }

    # 1. /api/v1/oracle/verify/niobium-scandium
    resp1 = client.post(
        "/api/v1/oracle/verify/niobium-scandium",
        json=payload,
        headers={"X-Dev-Bypass": "true"},
    )
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert data1["status"] == "success"
    assert data1["audit_verdict"]["is_compliant"] is True
    assert data1["audit_verdict"]["geofence_verified"] is True
    assert data1["onchain_signature"] is not None

    # 2. Dual endpoint /api/v1/niobium-scandium/verify-origin
    resp2 = client.post(
        "/api/v1/niobium-scandium/verify-origin",
        json=payload,
        headers={"X-Dev-Bypass": "true"},
    )
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["status"] == "success"
    assert data2["audit_verdict"]["grade_assay_certified"] is True


def test_mcp_verify_niobium_scandium_origin_tool():
    """Verify verify_niobium_scandium_origin tool registration and execution in MCP stdio handler."""
    # 1. Tools list contains verify_niobium_scandium_origin
    tools_list = handle_tools_list("req_nb_list")
    tool_names = [t["name"] for t in tools_list["result"]["tools"]]
    assert "verify_niobium_scandium_origin" in tool_names

    # 2. Execute tool call via stdio
    call_res = handle_tool_call(
        "req_nb_call",
        "verify_niobium_scandium_origin",
        {
            "batch_id": "NB-MCP-001",
            "tenement_id": "ELK_CREEK",
            "latitude": 40.274,
            "longitude": -96.183,
            "commodity_type": "FERRONIOBIUM",
            "fe_nb_grade_pct": 67.0,
            "doe_exim_loan_eligible": True,
            "ndaa_defense_procurement_eligible": True,
            "source_country": "USA",
        },
    )
    assert "result" in call_res
    content = json.loads(call_res["result"]["content"][0]["text"])
    assert content["status"] == "success"
    assert content["audit_verdict"]["is_compliant"] is True
    assert content["audit_verdict"]["geofence_verified"] is True
    assert content["audit_verdict"]["doe_exim_loan_eligible"] is True
