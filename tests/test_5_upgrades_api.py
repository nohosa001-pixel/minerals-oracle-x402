"""
Integration HTTP Tests for the 5 Major Upgrade API Endpoints in FastAPI app/main.py.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_api_rare_earths_verify():
    payload = {
        "batch_id": "RE-HTTP-001",
        "tenement_id": "MT_WELD",
        "latitude": -28.868,
        "longitude": 122.500,
        "ndpr_oxide_purity_pct": 99.60,
        "thorium_uranium_radiation_ppm": 40.0,
        "declared_china_origin_ratio": 0.0005,
        "source_country": "AUS",
    }
    response = client.post("/api/v1/rare-earths/verify-origin", json=payload, headers={"referer": "http://localhost:8000/dashboard"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["audit_verdict"]["is_compliant"] is True
    assert data["audit_verdict"]["mofcom_rule_d35_eligible"] is True


def test_api_tungsten_verify():
    payload = {
        "batch_id": "W-HTTP-001",
        "tenement_id": "CANTUNG",
        "latitude": 61.954,
        "longitude": -128.243,
        "apt_wo3_grade_pct": 89.2,
        "dodd_frank_conflict_free": True,
        "ndaa_defense_procurement_eligible": True,
        "source_country": "CAN",
    }
    response = client.post("/api/v1/tungsten/verify-origin", json=payload, headers={"referer": "http://localhost:8000/dashboard"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["audit_verdict"]["is_compliant"] is True
    assert data["audit_verdict"]["ndaa_defense_eligible"] is True


def test_api_black_mass_verify():
    payload = {
        "batch_id": "BM-HTTP-001",
        "facility_id": "ABTC_NEVADA",
        "latitude": 39.608,
        "longitude": -119.251,
        "nickel_content_pct": 22.0,
        "cobalt_content_pct": 8.0,
        "lithium_content_pct": 4.0,
        "fluorine_impurity_ppm": 150.0,
        "bis_export_license_id": "BIS-D112233",
        "recycled_content_ratio": 0.90,
        "source_country": "USA",
    }
    response = client.post("/api/v1/black-mass/verify-origin", json=payload, headers={"referer": "http://localhost:8000/dashboard"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["audit_verdict"]["bis_license_verified"] is True


def test_api_cbam_markup_penalty():
    payload = {
        "import_year": 2026,
        "product_category": "STEEL",
        "tonnage": 500.0,
        "default_embedded_emissions_tco2_per_ton": 2.2,
        "verified_scope1_2_emissions_tco2_per_ton": None,
        "eu_allowance_price_eur": 85.0,
    }
    response = client.post("/api/v1/regulatory/cbam/markup-penalty", json=payload, headers={"referer": "http://localhost:8000/dashboard"})
    assert response.status_code == 200
    data = response.json()
    assert data["markup_penalty_rate"] == 0.10
    assert data["markup_penalty_surcharge_eur"] > 0


def test_api_customs_clearance_verify():
    payload = {
        "tracking_type": "BOL",
        "tracking_number": "MEDU99887766",
        "carrier_code": "MSCU",
        "port_of_loading": "CLPRA",
        "port_of_discharge": "NLRTM",
        "departure_date": "2026-09-01",
        "arrival_date": "2026-09-24",
        "mineral_batch_id": "CU-LOT-777",
        "mine_coordinates": [-22.283, -68.900],
        "gross_weight_kg": 40000.0,
    }
    response = client.post("/api/v1/logistics/customs-clearance-verify", json=payload, headers={"referer": "http://localhost:8000/dashboard"})
    assert response.status_code == 200
    data = response.json()
    assert data["customs_clearance_eligible"] is True
    assert "bundle_id" in data["customs_clearance_bundle"]


def test_api_zk_proof_flow():
    # 1. Generate
    gen_payload = {
        "batch_id": "ZK-API-001",
        "secret_mine_latitude": -24.267,
        "secret_mine_longitude": -69.067,
        "secret_unit_cost_usd": 3800.0,
        "secret_supplier_id": "SECRET-MINER-1",
        "public_authorized_zone_root": "0xroot11223344",
        "public_china_origin_ratio": 0.0002,
        "public_max_carbon_kg_co2": 100.0,
    }
    gen_resp = client.post("/api/v1/zk/compliance-proof/generate", json=gen_payload, headers={"referer": "http://localhost:8000/dashboard"})
    assert gen_resp.status_code == 200
    gen_data = gen_resp.json()
    assert gen_data["is_valid_zero_knowledge_proof"] is True

    # 2. Verify
    ver_payload = {
        "zk_proof": gen_data["zk_proof"],
        "public_commitment": gen_data["public_commitment"],
        "nullifier_hash": gen_data["nullifier_hash"],
        "public_authorized_zone_root": "0xroot11223344",
        "public_china_origin_ratio": 0.0002,
    }
    ver_resp = client.post("/api/v1/zk/compliance-proof/verify", json=ver_payload, headers={"referer": "http://localhost:8000/dashboard"})
    assert ver_resp.status_code == 200
    ver_data = ver_resp.json()
    assert ver_data["is_valid"] is True


def test_api_x402_challenge_returned_when_unauthorized():
    # Calling without any authorization or referer triggers HTTP 402 Payment Required
    gen_payload = {
        "batch_id": "ZK-NOAUTH-001",
        "secret_mine_latitude": -24.267,
        "secret_mine_longitude": -69.067,
        "secret_unit_cost_usd": 3800.0,
        "secret_supplier_id": "SECRET-MINER-1",
        "public_authorized_zone_root": "0xroot11223344",
        "public_china_origin_ratio": 0.0002,
        "public_max_carbon_kg_co2": 100.0,
    }
    resp = client.post(
        "/api/v1/zk/compliance-proof/generate",
        json=gen_payload,
        headers={"X-Trial-Bypass": "true"}  # Forces x402 challenge
    )
    assert resp.status_code == 402
    assert "x402" in resp.headers.get("www-authenticate", "").lower() or resp.json().get("detail") is not None

