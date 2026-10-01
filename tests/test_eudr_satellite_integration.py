"""
Tests for EUDR Satellite Compliance Integration in minerals-oracle-x402.
Verifies eudr_client, ComplianceEngine geospatial audit, MCP tool, and FastAPI endpoint.
"""

import pytest
from fastapi.testclient import TestClient

from app.eudr_client import EUDRClient, eudr_client
from app.compliance_engine import compliance_engine
from app.schemas import (
    MineralLotProvenanceRequest,
    MineralType,
    SourceCountry,
    MinePermitsRecord,
    EcologicalSpatialRecord,
    LaborHumanRightsRecord,
    RefiningMassBalanceRecord,
    MaritimeLogisticsRecord,
    MaritimeCIIRating,
    GeopoliticalSanctionsRecord,
    MineSiteSatelliteAuditRequest,
)
from app.mcp_stdio import process_mcp_request
from app.main import app

client = TestClient(app)


def test_eudr_client_health():
    """Verifies that EUDR client health check returns valid telemetry."""
    res = eudr_client.check_health()
    assert "status" in res
    assert "latency_ms" in res
    assert res["status"] in ("HEALTHY", "UNREACHABLE") or res["status"].startswith("HTTP_")


@pytest.mark.asyncio
async def test_eudr_client_health_async():
    """Verifies non-blocking async health check."""
    res = await eudr_client.check_health_async()
    assert "status" in res
    assert "latency_ms" in res


def test_eudr_circuit_breaker():
    """Verifies that circuit breaker handles failures gracefully and resets."""
    custom_client = EUDRClient()
    assert custom_client.get_circuit_status()["state"] == "CLOSED"

    # Trip the circuit with 3 consecutive failures
    custom_client.record_failure(Exception("Probe failure 1"))
    custom_client.record_failure(Exception("Probe failure 2"))
    custom_client.record_failure(Exception("Probe failure 3"))

    status = custom_client.get_circuit_status()
    assert status["state"] == "OPEN"
    assert not custom_client.can_attempt_remote()

    # Reset circuit
    custom_client.record_success()
    assert custom_client.get_circuit_status()["state"] == "CLOSED"
    assert custom_client.can_attempt_remote()


def test_eudr_verify_mine_site_clean():
    """Verifies satellite compliance for clean mining coordinates."""
    # Sulawesi Indonesia Morowali nickel area
    res = eudr_client.verify_mine_site_compliance(
        latitude=-2.55,
        longitude=121.35,
        country_code="ID",
        area_hectares=12.5,
        concession_id="MINE-IDN-SULAWESI-01"
    )
    assert res["is_compliant"] is True
    assert res["deforestation_detected"] is False
    assert res["forest_loss_pct"] == 0.0
    assert res["indigenous_territory_encroachment"] is False
    assert res["satellite_evidence_hash"].startswith("0x")
    assert len(res["satellite_evidence_hash"]) == 66
    assert res["traces_nt_dds_reference"].startswith("DDS-EUDR-2026-ID-")
    assert res["audit_source"] in ("REMOTE_EUDR_AGENT", "LOCAL_SATELLITE_STANDALONE")


def test_eudr_verify_invalid_coordinates():
    """Verifies coordinate range validation error."""
    res = eudr_client.verify_mine_site_compliance(
        latitude=120.0,  # Invalid latitude > 90
        longitude=200.0,
        country_code="ID"
    )
    assert res["is_compliant"] is False
    assert res["deforestation_detected"] is True
    assert res["audit_source"] == "VALIDATION_ERROR"


def test_eudr_verify_deforestation_detection():
    """Verifies that synthetic deforestation triggers are correctly flagged."""
    res = eudr_client.verify_mine_site_compliance(
        latitude=-88.88,
        longitude=88.88,
        country_code="BR"
    )
    assert res["is_compliant"] is False
    assert res["deforestation_detected"] is True
    assert res["forest_loss_pct"] > 0.0


def test_eudr_verify_indigenous_encroachment():
    """Verifies that indigenous territory encroachment is correctly detected."""
    res = eudr_client.verify_mine_site_compliance(
        latitude=-77.77,
        longitude=77.77,
        country_code="BRA"
    )
    assert res["is_compliant"] is False
    assert res["indigenous_territory_encroachment"] is True


def test_compliance_engine_populates_satellite_proof():
    """Verifies that ComplianceEngine automatically attaches satellite proof and TRACES-NT DDS."""
    req = MineralLotProvenanceRequest(
        lot_id="LOT-IDN-TEST-EUDR-01",
        mineral_type=MineralType.NICKEL_MHP,
        source_country=SourceCountry.IDN,
        net_weight_metric_tons=500.0,
        declared_purity_pct=99.9,
        mine_permits=MinePermitsRecord(
            mining_license_id="IUP-OP-9981-IDN",
            mine_operator_name="PT Vale Indonesia Tbk",
            simbara_ntpn="NTPN-8829-VALID-IDN",
            dhe_forex_deposit_ref="DHE-BI-9921-OK"
        ),
        ecological_spatial=EcologicalSpatialRecord(
            latitude=-2.55,
            longitude=121.35,
            eudr_deforestation_free=True
        ),
        labor_human_rights=LaborHumanRightsRecord(),
        refining_mass_balance=RefiningMassBalanceRecord(
            refinery_id="REF-IMIP-01",
            feedstock_input_metric_tons=500.0,
            refined_output_metric_tons=490.0,
            recovery_yield_pct=98.0,
            mass_balance_loss_discrepancy_pct=1.0
        ),
        maritime_logistics=MaritimeLogisticsRecord(
            vessel_imo_number=9876543,
            vessel_name="MV PACIFIC GREEN",
            cii_rating=MaritimeCIIRating.A,
            ebl_document_hash="0x" + "a" * 64,
            iso_17025_lab_coa_hash="0x" + "b" * 64
        ),
        geopolitical_sanctions=GeopoliticalSanctionsRecord(
            feoc_shareholding_pct=0.0,
            feoc_board_control_pct=0.0,
            contractual_operational_control=False,
            us_substantial_transformation_compliant=True
        )
    )

    passport = compliance_engine.evaluate_lot(req)
    assert req.ecological_spatial.satellite_evidence_hash is not None
    assert req.ecological_spatial.satellite_evidence_hash.startswith("0x")
    assert req.ecological_spatial.traces_nt_dds_reference is not None
    assert "DDS-EUDR-2026-" in req.ecological_spatial.traces_nt_dds_reference
    assert any("DEFENSE_EUDR_DEFORESTATION_FREE" in d for d in passport.verdict.gotcha_defenses_applied)
    assert passport.verdict.eudr_deforestation_cleared is True


def test_compliance_engine_satellite_deforestation_violation():
    """Verifies that satellite deforestation detection results in a fatal violation."""
    req = MineralLotProvenanceRequest(
        lot_id="LOT-DEFOREST-TEST",
        mineral_type=MineralType.NICKEL_MHP,
        source_country=SourceCountry.IDN,
        net_weight_metric_tons=500.0,
        declared_purity_pct=99.9,
        mine_permits=MinePermitsRecord(
            mining_license_id="IUP-OP-9981-IDN",
            mine_operator_name="PT Vale Indonesia Tbk",
            simbara_ntpn="NTPN-8829-VALID-IDN",
            dhe_forex_deposit_ref="DHE-BI-9921-OK"
        ),
        ecological_spatial=EcologicalSpatialRecord(
            latitude=-88.88,  # Triggers deforestation flag in mock
            longitude=88.88,
            eudr_deforestation_free=True
        ),
        labor_human_rights=LaborHumanRightsRecord(),
        refining_mass_balance=RefiningMassBalanceRecord(
            refinery_id="REF-IMIP-01",
            feedstock_input_metric_tons=500.0,
            refined_output_metric_tons=490.0,
            recovery_yield_pct=98.0,
            mass_balance_loss_discrepancy_pct=1.0
        ),
        maritime_logistics=MaritimeLogisticsRecord(
            vessel_imo_number=9876543,
            vessel_name="MV PACIFIC GREEN",
            cii_rating=MaritimeCIIRating.A,
            ebl_document_hash="0x" + "a" * 64,
            iso_17025_lab_coa_hash="0x" + "b" * 64
        ),
        geopolitical_sanctions=GeopoliticalSanctionsRecord(
            feoc_shareholding_pct=0.0,
            feoc_board_control_pct=0.0,
            contractual_operational_control=False,
            us_substantial_transformation_compliant=True
        )
    )

    passport = compliance_engine.evaluate_lot(req)
    assert passport.verdict.is_fully_compliant is False
    assert passport.verdict.eudr_deforestation_cleared is False
    assert req.ecological_spatial.eudr_deforestation_free is False


def test_mcp_eudr_satellite_tool():
    """Verifies that the MCP stdio tool eudr_satellite_mine_audit runs cleanly."""
    rpc_request = {
        "jsonrpc": "2.0",
        "id": "test-eudr-001",
        "method": "tools/call",
        "params": {
            "name": "eudr_satellite_mine_audit",
            "arguments": {
                "latitude": -2.55,
                "longitude": 121.35,
                "country_code": "ID",
                "area_hectares": 15.0,
                "concession_id": "PT-VALE-SOROWAKO"
            }
        }
    }
    res = process_mcp_request(rpc_request)
    assert res is not None
    assert "result" in res
    assert "content" in res["result"]
    import json
    data = json.loads(res["result"]["content"][0]["text"])
    assert data["is_compliant"] is True
    assert data["satellite_evidence_hash"].startswith("0x")
    assert data["traces_nt_dds_reference"].startswith("DDS-EUDR-2026-ID-")


def test_api_eudr_satellite_audit_endpoint():
    """Verifies POST /api/v1/compliance/eudr-satellite-audit endpoint."""
    resp = client.post(
        "/api/v1/compliance/eudr-satellite-audit",
        json={
            "latitude": -2.55,
            "longitude": 121.35,
            "country_code": "ID",
            "area_hectares": 20.0,
            "concession_id": "WEDA-BAY-NICKEL-01"
        }
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert "traces_nt_dds_reference" in data


def test_eudr_boundary_coordinates_and_smallholder_point():
    """Verifies that coordinates at exact boundaries (-90, 180) and smallholder plots (<4ha) evaluate cleanly."""
    # Under 4ha: valid as Point
    res_point = eudr_client.verify_mine_site_compliance(
        latitude=-15.5,
        longitude=-47.5,
        country_code="BRA",
        area_hectares=2.5,
        concession_id="SMALLHOLDER-MINE-01"
    )
    assert res_point["is_compliant"] is True
    assert res_point["satellite_evidence_hash"].startswith("0x")

    # Extreme boundaries
    res_north = eudr_client.verify_mine_site_compliance(
        latitude=89.99,
        longitude=179.99,
        country_code="NOR",
        area_hectares=5.0
    )
    assert res_north["is_compliant"] is True


def test_eudr_concurrent_execution():
    """Verifies thread-safety under concurrent multi-agent queries."""
    from concurrent.futures import ThreadPoolExecutor

    def run_check(i):
        lat = -2.0 + (i * 0.01)
        lon = 120.0 + (i * 0.01)
        return eudr_client.verify_mine_site_compliance(
            latitude=lat,
            longitude=lon,
            country_code="ID",
            area_hectares=10.0,
            concession_id=f"MINE-PARALLEL-{i}"
        )

    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(run_check, range(16)))

    assert len(results) == 16
    for r in results:
        assert r["satellite_evidence_hash"].startswith("0x")
        assert "DDS-EUDR-2026-" in r["traces_nt_dds_reference"]


def test_eudr_strict_mode_fail_closed():
    """Verifies fail-closed behavior when strict mode is active and agent is unreachable."""
    strict_client = EUDRClient()
    strict_client.strict_mode = True
    strict_client.agent_url = "http://127.0.0.1:9999"  # Non-existent endpoint

    res = strict_client.verify_mine_site_compliance(
        latitude=-2.55,
        longitude=121.35,
        country_code="ID",
        area_hectares=10.0
    )
    assert res["is_compliant"] is False
    assert res["audit_source"] == "FAIL_CLOSED_ERROR"
    assert "Fail-Closed" in res["reason"]


def test_api_eudr_validation_error():
    """Verifies that out-of-range coordinates are rejected with HTTP 422."""
    resp = client.post(
        "/api/v1/compliance/eudr-satellite-audit",
        json={
            "latitude": 999.0,  # Invalid latitude > 90
            "longitude": 121.35,
            "country_code": "ID",
            "area_hectares": 10.0
        }
    )
    assert resp.status_code == 422

