"""
Unit and integration tests for On-Chain Smart Contract Binding & EIP-712 Signatures.
"""

import pytest
from fastapi.testclient import TestClient
from eth_account import Account
from eth_account.messages import encode_typed_data
from web3 import Web3

from app.main import app
from app.onchain_signer import onchain_signer, OnChainOracleSigner
from app.mcp_stdio import handle_tools_list, handle_tool_call


client = TestClient(app)


def test_eip712_price_feed_signature_recovery():
    """Verifies that the generated (v, r, s) signature can be recovered to the exact signer address."""
    symbol = "Cu"
    spot_price = 9650.50
    round_id = 2001
    timestamp = 1720000000

    signed_data = onchain_signer.sign_price_feed(
        symbol=symbol,
        price_usd=spot_price,
        round_id=round_id,
        timestamp=timestamp,
    )

    feed = signed_data["feed"]
    sig = signed_data["signature"]
    calldata = signed_data["calldata"]

    assert feed["symbol"] == "Cu"
    assert feed["spotPriceUsd"] == 9650.50
    assert feed["spotPriceUsd8Dec"] == 965050000000  # 9650.50 * 10^8
    assert feed["roundId"] == 2001
    assert feed["timestamp"] == 1720000000

    assert sig["v"] in (27, 28)
    assert sig["r"].startswith("0x") and len(sig["r"]) == 66
    assert sig["s"].startswith("0x") and len(sig["s"]) == 66
    assert calldata.startswith("0x")

    # Reconstruct typed data message to verify cryptographic signature recovery
    types = {
        "EIP712Domain": [
            {"name": "name", "type": "string"},
            {"name": "version", "type": "string"},
            {"name": "chainId", "type": "uint256"},
            {"name": "verifyingContract", "type": "address"},
        ],
        "MineralPriceFeed": [
            {"name": "symbol", "type": "string"},
            {"name": "spotPriceUsd8Dec", "type": "uint256"},
            {"name": "timestamp", "type": "uint256"},
            {"name": "roundId", "type": "uint256"},
        ],
    }

    message = {
        "symbol": symbol,
        "spotPriceUsd8Dec": feed["spotPriceUsd8Dec"],
        "timestamp": timestamp,
        "roundId": round_id,
    }

    typed_data = {
        "types": types,
        "primaryType": "MineralPriceFeed",
        "domain": onchain_signer.get_domain_data(),
        "message": message,
    }

    signable_msg = encode_typed_data(full_message=typed_data)
    recovered = Account.recover_message(signable_msg, signature=bytes.fromhex(sig["fullSignature"]))
    assert recovered.lower() == onchain_signer.signer_address.lower()


def test_eip712_scrap_settlement_signature_recovery():
    """Verifies that the generated scrap settlement signature recovers correctly."""
    category = "EV_BATTERY_BLACK_MASS"
    net_value_usd = 12500.75
    quantity_kg = 5000.0
    batch_id = "0x" + "a" * 64
    timestamp = 1720000000

    signed_data = onchain_signer.sign_scrap_settlement(
        scrap_category=category,
        net_value_usd=net_value_usd,
        quantity_kg=quantity_kg,
        batch_id=batch_id,
        timestamp=timestamp,
    )

    settlement = signed_data["settlement"]
    sig = signed_data["signature"]

    assert settlement["scrapCategory"] == category
    assert settlement["netValueUsd8Dec"] == 1250075000000
    assert settlement["quantityKg"] == 5000
    assert settlement["batchId"] == batch_id

    types = {
        "EIP712Domain": [
            {"name": "name", "type": "string"},
            {"name": "version", "type": "string"},
            {"name": "chainId", "type": "uint256"},
            {"name": "verifyingContract", "type": "address"},
        ],
        "ScrapSettlement": [
            {"name": "scrapCategory", "type": "string"},
            {"name": "netValueUsd8Dec", "type": "uint256"},
            {"name": "quantityKg", "type": "uint256"},
            {"name": "timestamp", "type": "uint256"},
            {"name": "batchId", "type": "bytes32"},
        ],
    }

    message = {
        "scrapCategory": category,
        "netValueUsd8Dec": settlement["netValueUsd8Dec"],
        "quantityKg": 5000,
        "timestamp": timestamp,
        "batchId": bytes.fromhex(batch_id[2:]),
    }

    typed_data = {
        "types": types,
        "primaryType": "ScrapSettlement",
        "domain": onchain_signer.get_domain_data(),
        "message": message,
    }

    signable_msg = encode_typed_data(full_message=typed_data)
    recovered = Account.recover_message(signable_msg, signature=bytes.fromhex(sig["fullSignature"]))
    assert recovered.lower() == onchain_signer.signer_address.lower()


def test_api_onchain_payload_endpoint():
    """Tests GET /api/v1/oracle/onchain-payload/{symbol} endpoint."""
    headers = {"X-Dev-Bypass": "true"}
    resp = client.get("/api/v1/oracle/onchain-payload/Cu", headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    assert "feed" in data
    assert "signature" in data
    assert "calldata" in data
    assert data["feed"]["symbol"] == "Cu"
    assert data["feed"]["spotPriceUsd8Dec"] > 0
    assert data["calldata"].startswith("0x")


def test_api_onchain_settlement_endpoint():
    """Tests POST /api/v1/oracle/onchain-settlement-payload endpoint."""
    headers = {"X-Dev-Bypass": "true"}
    payload = {
        "scrap_category": "EV_BATTERY_BLACK_MASS",
        "quantity_metric_tons": 2.5,
        "target_yield_currency": "USDC",
    }
    resp = client.post("/api/v1/oracle/onchain-settlement-payload", json=payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    assert "settlement" in data
    assert "signature" in data
    assert "calldata" in data
    assert data["settlement"]["quantityKg"] == 2500
    assert data["settlement"]["netValueUsd8Dec"] > 0


def test_mcp_stdio_onchain_tool():
    """Tests MCP stdio get_onchain_signed_feed tool."""
    tools_resp = handle_tools_list(req_id="test-1")
    tool_names = [t["name"] for t in tools_resp["result"]["tools"]]
    assert "get_onchain_signed_feed" in tool_names

    call_resp = handle_tool_call(
        req_id="test-2",
        name="get_onchain_signed_feed",
        args={"symbol": "Li"},
    )
    assert "result" in call_resp
    text_content = call_resp["result"]["content"][0]["text"]
    assert "spotPriceUsd8Dec" in text_content
    assert "calldata" in text_content
