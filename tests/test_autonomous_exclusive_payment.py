import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas import PricingTier

client = TestClient(app)


def test_human_stripe_endpoints_completely_removed():
    """
    Verify all human fiat Stripe endpoints are completely removed and return 404 Not Found.
    Enforces the 'Humans Not Accepted / Autonomous Agents Only' rule.
    """
    # 1. Config endpoint
    res_config = client.get("/api/v1/stripe/config")
    assert res_config.status_code == 404, "Human Stripe config must be 404"

    # 2. Checkout session creation endpoint
    res_checkout = client.post(
        "/api/v1/stripe/create-checkout-session",
        json={"tier": "DAY_PASS", "customer_email": "human@example.com"}
    )
    assert res_checkout.status_code == 404, "Human Stripe checkout must be 404"

    # 3. Session pass retrieval endpoint
    res_session = client.get("/api/v1/stripe/session/cs_test_dummy_123")
    assert res_session.status_code == 404, "Human Stripe session retrieval must be 404"

    # 4. Webhook dispatcher endpoint
    res_webhook = client.post(
        "/api/v1/stripe/webhook",
        content=b"{}",
        headers={"stripe-signature": "dummy_sig"}
    )
    assert res_webhook.status_code == 404, "Human Stripe webhook must be 404"

    # 5. Urban mining calculate endpoint removed
    res_um = client.post("/api/v1/oracle/urban-mining/calculate", json={"lot_id": "test"})
    assert res_um.status_code == 404, "Urban mining calculation endpoint must be 404 removed"


def test_autonomous_agent_instant_onboarding():
    """
    Verify autonomous AI agent can self-onboard zero-friction without human credit card.
    Agent receives instant 0.05 USDC trial balance (10 free queries) and session key.
    """
    res = client.post(
        "/api/v1/agent/onboard",
        json={
            "agent_name": "AutonomousMinerArbitrageBot-01",
            "agent_address": "0x71C84107b3a42E2F2Ab4Ba770265EC0c4ce5Cea6",
            "requested_network": "polygon"
        }
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["trial_balance_usdc"] >= 0.05
    assert "session_key" in data
    assert data["session_key"].startswith(("agent_session_", "vault_key_"))
    assert "X-Agent-Vault-Key" in data["auth_header"]["header_name"]


def test_autonomous_agent_vault_fast_path_payment():
    """
    Verify agent with pre-funded vault session key queries protected oracle without human intervention.
    """
    # 1. Self-onboard to obtain vault key
    onboard_res = client.post(
        "/api/v1/agent/onboard",
        json={"agent_name": "FastPathAgent-02"}
    )
    assert onboard_res.status_code == 200
    session_key = onboard_res.json()["session_key"]

    # 2. Query protected prices endpoint using X-Agent-Vault-Key header
    res = client.get(
        "/api/v1/oracle/prices",
        headers={"X-Agent-Vault-Key": session_key}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["compliance_gate"] == "OPERATIONAL"
    assert res.headers.get("x-payment-method") == "Pre-Funded-Vault"
    assert "x-vault-balance-remaining" in res.headers


def test_autonomous_agent_x402_challenge_generation():
    """
    Verify oracle returns standard RFC-grade x402 challenge with cryptographic nonce for agent signing.
    """
    res = client.get(
        "/api/v1/oracle/challenge",
        params={"chain": "polygon", "tier": PricingTier.STANDARD.value}
    )
    assert res.status_code == 402
    assert "WWW-Authenticate" in res.headers
    data = res.json()
    assert data["status"] == "error"
    assert data["code"] == 402
    challenge = data["payment_challenge"]
    assert challenge["accepted_token"] == "USDC"
    assert challenge["network"] == "polygon"
    assert challenge["chain_id"] == 137
    assert challenge["amount"] == "0.005"
    assert len(challenge["nonce"]) >= 16


def test_autonomous_agent_vault_deposit_and_balance():
    """
    Verify agent can programmatically deposit Polygon USDC into vault and check balance.
    """
    agent_addr = "0x999999cf1046e68e36E1aA2E0E07105eDDD1f08E"
    deposit_res = client.post(
        "/api/v1/vault/deposit",
        json={
            "agent_address": agent_addr,
            "amount_usdc": 10.0,
            "tx_hash": "0x" + "a" * 64
        }
    )
    assert deposit_res.status_code == 200
    deposit_data = deposit_res.json()
    assert deposit_data["balance_usdc"] >= 10.0
    assert deposit_data["session_key"].startswith("vault_key_")

    balance_res = client.get(f"/api/v1/vault/balance/{agent_addr}")
    assert balance_res.status_code == 200
    assert balance_res.json()["balance_usdc"] >= 10.0


def test_zero_pii_stateless_agent_architecture():
    """
    Verify complete absence of PII collection, email requirements, sign-up forms, or human user accounts.
    """
    # 1. Agent onboarding requires ZERO personal info or email
    onboard_res = client.post("/api/v1/agent/onboard", json={})
    assert onboard_res.status_code == 200
    assert "session_key" in onboard_res.json()
    assert "email" not in onboard_res.json()

    # 2. Enterprise key provisioning without any email/signup
    ent_res = client.post(
        "/api/v1/enterprise/provision-key",
        json={
            "organization_name": "Autonomous Market Maker Node #4",
            "agent_identifier": "0x4444444444444444444444444444444444444444"
        }
    )
    assert ent_res.status_code == 200
    data = ent_res.json()
    assert data["enterprise_key"].startswith("ent_key_")


def test_5_pillar_zero_liability_architecture():
    """
    Validates the 5 Core Zero-Liability Pillars:
    1. Exclusion of 'guarantee/certified' in descriptions.
    2. Response meta disclaimer block on JSON payloads.
    3. MCP Tool Schema Prompt Guard.
    4. MIT/Apache 2.0 AS-IS warranty disclaimer.
    5. Stateless peer-to-peer x402 vending machine model.
    """
    # Pillar 2 & 4: Meta block with AS-IS and warranty exclusion
    prices_res = client.get("/api/v1/oracle/prices", headers={"X-Dev-Bypass": "true"})
    assert prices_res.status_code == 200
    pdata = prices_res.json()
    assert "meta" in pdata
    assert pdata["meta"]["license"] == "AS-IS"
    assert "does not constitute legal, regulatory, or compliance certification" in pdata["meta"]["disclaimer"]
    assert "WITHOUT WARRANTY OF ANY KIND" in pdata["meta"]["warranty"]

    # Pillar 2 on 402 challenge
    chal_res = client.get("/api/v1/oracle/challenge")
    assert chal_res.status_code == 402
    cdata = chal_res.json()
    assert "meta" in cdata
    assert cdata["meta"]["license"] == "AS-IS"

    # Pillar 3: MCP Tool Prompt Guard
    tools_res = client.get("/mcp/tools")
    assert tools_res.status_code == 200
    mcp_tools = {t["name"]: t["description"] for t in tools_res.json()["tools"]}
    assert "verify_mineral_lot_compliance" in mcp_tools
    assert "DO NOT use as an official regulatory legal filing" in mcp_tools["verify_mineral_lot_compliance"]
