import json
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from app.main import app
from app.a2a_deal_engine import get_a2a_deal_engine, DealNotFoundError, InvalidDealStateError
from app.schemas import (
    TradeDealSpec,
    TradeDealProposeRequest,
    TradeDealDualSignRequest,
    MineralType,
    SourceCountry,
)


@pytest.fixture
def client():
    return TestClient(app)


def test_escrow_artifact_validity():
    """Validates the exported MineralTradeEscrow JSON artifact and ABI structure."""
    artifact_path = Path(__file__).parent.parent / "contracts" / "artifacts" / "MineralTradeEscrow.json"
    assert artifact_path.exists(), "Artifact MineralTradeEscrow.json should exist"

    with open(artifact_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["contractName"] == "MineralTradeEscrow"
    abi = data["abi"]
    function_names = [item["name"] for item in abi if item.get("type") == "function"]
    assert "createEscrow" in function_names
    assert "releaseStage1BL" in function_names
    assert "releaseStage2Transit" in function_names
    assert "completeEscrow" in function_names
    assert "refundExpiredDeal" in function_names
    assert "getDeal" in function_names

    event_names = [item["name"] for item in abi if item.get("type") == "event"]
    assert "EscrowCreated" in event_names
    assert "Stage1Released" in event_names
    assert "Stage2Released" in event_names
    assert "EscrowCompleted" in event_names
    assert "EscrowRefunded" in event_names


def test_escrow_calldata_generation_and_api(client):
    """Verifies end-to-end deal proposal, dual-signing, and escrow calldata generation."""
    deal_engine = get_a2a_deal_engine()
    deal_id = "deal_escrow_test_001"
    seller_addr = "0x1111111111111111111111111111111111111111"
    buyer_addr = "0x2222222222222222222222222222222222222222"

    spec = TradeDealSpec(
        deal_id=deal_id,
        commodity=MineralType.LITHIUM_CARBONATE,
        volume_tons=50.0,
        unit_price_usd_per_ton=14000.0,
        total_deal_value_usd=700000.0,
        origin_country=SourceCountry.AUS,
        destination_country="KR",
        feoc_cleared=True,
        mass_balance_cleared=True,
        ebl_document_id="EBL-MAERSK-2026-LIT09",
        buyer_agent_address=buyer_addr,
        seller_agent_address=seller_addr,
        created_at_utc="2026-09-22T10:00:00Z",
    )

    seller_sig = "0x" + "a" * 130
    prop_req = TradeDealProposeRequest(spec=spec, seller_signature=seller_sig)
    deal_engine.propose_deal(prop_req)

    # Calling escrow calldata before dual-signing should raise 400 Bad Request
    resp_premature = client.get(f"/api/v1/a2a/deals/{deal_id}/escrow-calldata")
    assert resp_premature.status_code == 400
    assert "expected 'DUAL_SIGNED_CONFIRMED'" in resp_premature.json()["detail"]

    # Countersign deal
    buyer_sig = "0x" + "b" * 130
    dual_req = TradeDealDualSignRequest(deal_id=deal_id, buyer_agent_address=buyer_addr, buyer_signature=buyer_sig)
    deal_engine.dual_sign_deal(dual_req)

    # Calling escrow calldata directly via engine
    calldata_info = deal_engine.build_escrow_deposit_calldata(deal_id)
    assert calldata_info["deal_id"] == deal_id
    assert calldata_info["required_usdc_amount"] == 700000.0
    assert calldata_info["required_usdc_units"] == 700000000000
    assert calldata_info["calldata"].startswith("0x")
    assert len(calldata_info["calldata"]) > 10
    assert calldata_info["duration_seconds"] >= 60

    # Calling via FastAPI route
    resp = client.get(f"/api/v1/a2a/deals/{deal_id}/escrow-calldata")
    assert resp.status_code == 200
    data = resp.json()
    assert data["deal_id"] == deal_id
    assert data["required_usdc_units"] == 700000000000
    assert data["seller_agent_address"].lower() == seller_addr.lower()
    assert data["buyer_agent_address"].lower() == buyer_addr.lower()
    assert data["function_signature"] == "createEscrow(bytes32,address,uint256,bytes32,uint256)"

    # Test non-existent deal 404
    resp_404 = client.get("/api/v1/a2a/deals/non_existent_deal/escrow-calldata")
    assert resp_404.status_code == 404
