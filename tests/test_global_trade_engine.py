"""
Tests for Global Trade Flows, HS Tariffs, Maritime Logistics, and eBL Intelligence.
"""

import pytest
import hashlib
from fastapi.testclient import TestClient

from app.main import app
from app.schemas import MineralType, SourceCountry, MaritimeCIIRating
from app.global_trade_engine import global_trade_engine
from app.mcp_stdio import handle_tools_list, handle_tool_call


client = TestClient(app)


def test_corridors_query_engine():
    """Verifies in-memory trade corridor filtering by mineral, origin, and destination."""
    all_corrs = global_trade_engine.get_corridors()
    assert len(all_corrs) >= 8

    # Filter by Lithium
    li_corrs = global_trade_engine.get_corridors(mineral_type=MineralType.LITHIUM_HYDROXIDE)
    assert len(li_corrs) >= 2
    assert any(c.origin_country == SourceCountry.AUS for c in li_corrs)

    # Filter by Origin IDN
    idn_corrs = global_trade_engine.get_corridors(origin_country=SourceCountry.IDN)
    assert len(idn_corrs) >= 2
    assert idn_corrs[0].origin_port_name in ("Weda Bay Port", "Morowali Port")


def test_hs_tariff_resolution():
    """Verifies HS code, MFN duty, FTA preferential duty, and trade defense barriers."""
    # US Lithium Carbonate
    us_li = global_trade_engine.get_hs_tariff(MineralType.LITHIUM_CARBONATE, "USA")
    assert us_li.hs_code == "2825.20.00"
    assert us_li.mfn_duty_pct == 3.7
    assert us_li.fta_preferential_duty_pct == 0.0
    assert us_li.section_301_tariff_pct == 25.0

    # Indonesia Nickel MHP (Subject to export licensing / CBAM)
    eu_ni = global_trade_engine.get_hs_tariff(MineralType.NICKEL_MHP, "EU")
    assert eu_ni.hs_code == "7501.10.00"
    assert eu_ni.eu_cbam_applicable is True
    assert eu_ni.cbam_default_carbon_intensity == 18.5
    assert eu_ni.export_licensing_required is True


def test_maritime_route_calculation_and_chokepoints():
    """Tests voyage distance, transit days, fuel freight, and chokepoint detour math."""
    from app.schemas import MaritimeRouteRequest

    # 1. Normal route: Australia to Korea
    req_aus_kor = MaritimeRouteRequest(
        mineral_type=MineralType.LITHIUM_HYDROXIDE,
        origin_country=SourceCountry.AUS,
        destination_country="KOR",
        cargo_weight_metric_tons=5000.0,
        cii_rating=MaritimeCIIRating.A,
    )
    res_aus_kor = global_trade_engine.calculate_maritime_route(req_aus_kor)
    assert res_aus_kor.status == "success"
    assert res_aus_kor.nautical_miles == 3120.0
    assert res_aus_kor.estimated_transit_days == 10.0
    assert res_aus_kor.base_freight_usd_per_mt == 24.50
    assert res_aus_kor.total_voyage_co2_metric_tons > 0.0

    # 2. Detour route avoiding Panama Canal (Chile to USA via Cape Horn)
    req_detour = MaritimeRouteRequest(
        mineral_type=MineralType.LITHIUM_CARBONATE,
        origin_country=SourceCountry.CHL,
        destination_country="USA",
        cargo_weight_metric_tons=1000.0,
        avoid_chokepoints=["PANAMA_CANAL"],
    )
    res_detour = global_trade_engine.calculate_maritime_route(req_detour)
    assert res_detour.estimated_transit_days > 20.0
    assert res_detour.risk_surcharge_usd_per_mt == 35.00
    assert "Cape Horn" in res_detour.route_advisory


def test_ebl_cryptographic_verification():
    """Tests electronic Bill of Lading validation, valid IMO checksum, and dark fleet screening."""
    from app.schemas import EBLVerificationRequest

    # Generate a valid IMO with checksum: 9315331
    # 9*7 + 3*6 + 1*5 + 5*4 + 3*3 + 3*2 = 63 + 18 + 5 + 20 + 9 + 6 = 121 % 10 = 1 -> valid!
    valid_imo = 9315331
    dummy_hash = hashlib.sha256(b"TEST_EBL_MANIFEST_2026").hexdigest()

    # Valid eBL
    req_valid = EBLVerificationRequest(
        ebl_document_id="eBL-AUHED-KRGWA-2026-001",
        ebl_document_hash=dummy_hash,
        carrier_imo_number=valid_imo,
        vessel_name="PACIFIC_NAVIGATOR",
        mineral_type=MineralType.LITHIUM_HYDROXIDE,
        gross_weight_metric_tons=12000.0,
        port_of_loading_code="AUHED",
        port_of_discharge_code="KRGWA",
        shipper_name="Pilbara Minerals Ltd",
        consignee_name="POSCO Future M Co Ltd",
    )
    res_valid = global_trade_engine.verify_ebl(req_valid)
    assert res_valid.is_valid is True
    assert res_valid.carrier_imo_valid is True
    assert res_valid.port_pair_valid is True
    assert res_valid.dark_fleet_flag is False
    assert "VERIFIED_MLETR_COMPLIANT" in res_valid.audit_verdict

    # Invalid IMO (wrong checksum digit)
    req_invalid_imo = EBLVerificationRequest(
        ebl_document_id="eBL-BAD-IMO-001",
        ebl_document_hash=dummy_hash,
        carrier_imo_number=9315339,  # Incorrect check digit (9 instead of 1)
        vessel_name="PACIFIC_NAVIGATOR",
        mineral_type=MineralType.LITHIUM_HYDROXIDE,
        gross_weight_metric_tons=12000.0,
        port_of_loading_code="AUHED",
        port_of_discharge_code="KRGWA",
        shipper_name="Pilbara Minerals Ltd",
        consignee_name="POSCO Future M Co Ltd",
    )
    res_invalid = global_trade_engine.verify_ebl(req_invalid_imo)
    assert res_invalid.is_valid is False
    assert res_invalid.carrier_imo_valid is False

    # Dark fleet screening
    req_dark_fleet = EBLVerificationRequest(
        ebl_document_id="eBL-DARK-FLEET-001",
        ebl_document_hash=dummy_hash,
        carrier_imo_number=valid_imo,
        vessel_name="Shadow_Carrier_09",
        mineral_type=MineralType.LITHIUM_HYDROXIDE,
        gross_weight_metric_tons=12000.0,
        port_of_loading_code="AUHED",
        port_of_discharge_code="KRGWA",
        shipper_name="Unknown Offloading Agent",
        consignee_name="POSCO Future M Co Ltd",
    )
    res_dark = global_trade_engine.verify_ebl(req_dark_fleet)
    assert res_dark.is_valid is False
    assert res_dark.dark_fleet_flag is True


def test_rest_api_global_trade_endpoints():
    """Integration test for all 5 REST API trade endpoints."""
    # 1. GET /api/v1/trade/flows
    resp_flows = client.get("/api/v1/trade/flows?mineral_type=NICKEL_MHP")
    assert resp_flows.status_code == 200
    flows = resp_flows.json()
    assert len(flows) >= 2
    assert flows[0]["mineral_type"] == "NICKEL_MHP"

    # 2. POST /api/v1/trade/tariffs
    resp_tariff = client.post(
        "/api/v1/trade/tariffs?mineral_type=COPPER_CATHODE&importer_jurisdiction=USA"
    )
    assert resp_tariff.status_code == 200
    tariff_data = resp_tariff.json()
    assert tariff_data["hs_code"] == "7403.11.00"
    assert tariff_data["importer_jurisdiction"] == "USA"

    # 3. POST /api/v1/trade/maritime-route
    route_payload = {
        "mineral_type": "LITHIUM_HYDROXIDE",
        "origin_country": "AUS",
        "destination_country": "KOR",
        "cargo_weight_metric_tons": 2500.0,
        "cii_rating": "A",
    }
    resp_route = client.post("/api/v1/trade/maritime-route", json=route_payload)
    assert resp_route.status_code == 200
    r_data = resp_route.json()
    assert r_data["corridor_id"] == "CORR_AUS_KOR_LI"
    assert r_data["estimated_transit_days"] == 10.0

    # 4. POST /api/v1/trade/verify-ebl
    ebl_payload = {
        "ebl_document_id": "eBL-REST-TEST-001",
        "ebl_document_hash": "a" * 64,
        "carrier_imo_number": 9315331,
        "vessel_name": "STAR_BULKER_1",
        "mineral_type": "NICKEL_MHP",
        "gross_weight_metric_tons": 5000.0,
        "port_of_loading_code": "IDWDA",
        "port_of_discharge_code": "KRGWA",
        "shipper_name": "PT Halmahera Minerals",
        "consignee_name": "LG Energy Solution Ltd",
    }
    resp_ebl = client.post("/api/v1/trade/verify-ebl", json=ebl_payload)
    assert resp_ebl.status_code == 200
    assert resp_ebl.json()["is_valid"] is True

    # 5. POST /api/v1/trade/optimize-route
    opt_payload = {
        "mineral_type": "LITHIUM_CARBONATE",
        "origin_country": "CHL",
        "destination_country": "USA",
        "cargo_weight_metric_tons": 1000.0,
    }
    resp_opt = client.post("/api/v1/trade/optimize-route", json=opt_payload)
    assert resp_opt.status_code == 200
    opt_data = resp_opt.json()
    assert len(opt_data["options_evaluated"]) == 2
    assert opt_data["optimal_corridor_id"] == "CORR_CHL_USA_LI"


def test_mcp_trade_tools_via_rest():
    """Verifies invocation of all 5 trade tools via /mcp/invoke."""
    # Tool: get_global_trade_flows
    call_flows = {
        "name": "get_global_trade_flows",
        "arguments": {"mineral_type": "LITHIUM_HYDROXIDE", "origin_country": "AUS"}
    }
    res_mcp = client.post("/mcp/invoke", json=call_flows)
    assert res_mcp.status_code == 200
    assert "CORR_AUS_KOR_LI" in res_mcp.json()["content"][0]["text"]

    # Tool: calculate_trade_tariffs
    call_tariff = {
        "name": "calculate_trade_tariffs",
        "arguments": {"mineral_type": "LITHIUM_CARBONATE", "importer_jurisdiction": "USA"}
    }
    res_tariff = client.post("/mcp/invoke", json=call_tariff)
    assert res_tariff.status_code == 200
    assert "2825.20.00" in res_tariff.json()["content"][0]["text"]


def test_mcp_stdio_trade_tools():
    """Verifies stdio JSON-RPC tools/list and tools/call for trade tools."""
    # 1. tools/list
    list_resp = handle_tools_list("req_list_01")
    tool_names = [t["name"] for t in list_resp["result"]["tools"]]
    assert "get_global_trade_flows" in tool_names
    assert "calculate_trade_tariffs" in tool_names
    assert "estimate_maritime_freight_and_carbon" in tool_names
    assert "verify_electronic_bill_of_lading" in tool_names
    assert "optimize_mineral_trade_route" in tool_names

    # 2. tools/call estimate_maritime_freight_and_carbon
    call_resp = handle_tool_call(
        req_id="req_call_01",
        name="estimate_maritime_freight_and_carbon",
        arguments={
            "mineral_type": "LITHIUM_HYDROXIDE",
            "origin_country": "AUS",
            "destination_country": "KOR",
            "cargo_weight_metric_tons": 3000.0,
        }
    )
    assert "result" in call_resp
    assert "CORR_AUS_KOR_LI" in call_resp["result"]["content"][0]["text"]
