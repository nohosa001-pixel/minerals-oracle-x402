"""
Integration Tests for Solana Mainnet-Beta (Chain ID 501) Connectivity & Rails.
Validates:
1. Multi-Chain Registry configuration for Solana Mainnet (501, 400ms, SPL USDC, Solscan).
2. x402 Verifier payment challenges, headers, and on-chain signature verification with anti-replay protection.
3. Security Gate Client Ed25519 truth attestation (sync & async) and universal escrow settlement.
4. FastAPI Endpoints:
   - GET /api/v1/oracle/security-gate/status
   - POST /api/v1/escrow/universal/solana/attest
   - POST /api/v1/escrow/universal/settle-solana
5. Treasury routing to 411ksMz9RHYVtVMe6RUUErzZYtrU9zzvkgzswKbqx9qp.
"""

import pytest
import os
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient

from app.main import app
from app.multi_chain import (
    SupportedChain,
    get_chain_config,
    resolve_chain_name,
    is_chain_supported,
)
from app.x402_verifier import x402_verifier, PricingTier
from app.security_gate_client import security_gate_client

client = TestClient(app)


def test_solana_chain_configuration():
    """Verify Solana Mainnet is properly registered and configured in multi_chain module."""
    assert is_chain_supported("solana") is True
    assert is_chain_supported("sol") is True
    assert is_chain_supported("solana-mainnet") is True
    assert is_chain_supported(501) is True

    cfg = get_chain_config("solana")
    assert cfg.chain_id == 501
    assert cfg.display_name == "Solana Mainnet"
    assert cfg.usdc_address == "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
    assert cfg.speed_ms == 400
    assert "solscan.io" in cfg.explorer_url
    assert "solana.com" in cfg.rpc_url
    assert resolve_chain_name("solana") == "solana"


def test_x402_challenge_solana():
    """Verify x402 payment challenge generated for Solana Mainnet uses correct parameters."""
    challenge = x402_verifier.generate_challenge(
        tier=PricingTier.STANDARD,
        chain_name="solana",
    )

    assert challenge.network == "solana"
    assert challenge.chain_id == 501
    assert challenge.accepted_token == "USDC"
    assert challenge.token_address == "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
    assert challenge.recipient_address == os.getenv(
        "SOLANA_WALLET_ADDRESS", "411ksMz9RHYVtVMe6RUUErzZYtrU9zzvkgzswKbqx9qp"
    )

    resp_402 = x402_verifier.build_402_response(tier=PricingTier.STANDARD, chain_name="solana")
    assert resp_402.status_code == 402
    assert "solana" in resp_402.headers.get("X-Supported-Chains", "")
    assert "X-Payment-Recipient" in resp_402.headers
    assert resp_402.headers["X-Payment-Recipient"] == os.getenv(
        "SOLANA_WALLET_ADDRESS", "411ksMz9RHYVtVMe6RUUErzZYtrU9zzvkgzswKbqx9qp"
    )


def test_solana_signature_verification_and_anti_replay():
    """Verify Solana Base58 transaction signature verification and anti-replay protection."""
    import secrets
    # Base58 signature: exactly 88 characters (54 prefix + 34 random)
    rand_chars = "".join(secrets.choice("123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz") for _ in range(34))
    test_sig = "5VerBQQuJYvHiU1fXb6Vd99Q3aP3h6k6yqgXfCjE288jC2jVn8P6wM" + rand_chars

    # 1. Invalid signature character rejection
    bad_sig = "0OIl_invalid_base58_characters!!!"
    ok, reason = x402_verifier._verify_solana_onchain_tx(bad_sig, required_amount_usdc=0.05)
    assert ok is False
    assert reason is not None and "Invalid Solana transaction signature format" in reason

    # 2. Simulated successful verification
    with patch("httpx.Client.post") as mock_post:
        treasury_sol = "411ksMz9RHYVtVMe6RUUErzZYtrU9zzvkgzswKbqx9qp"
        usdc_mint = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "jsonrpc": "2.0",
            "result": {
                "slot": 240000000,
                "meta": {
                    "err": None,
                    "fee": 5000,
                    "preTokenBalances": [
                        {
                            "accountIndex": 1,
                            "mint": usdc_mint,
                            "owner": treasury_sol,
                            "uiTokenAmount": {"uiAmount": 10.0, "amount": "10000000", "decimals": 6}
                        }
                    ],
                    "postTokenBalances": [
                        {
                            "accountIndex": 1,
                            "mint": usdc_mint,
                            "owner": treasury_sol,
                            "uiTokenAmount": {"uiAmount": 10.05, "amount": "10050000", "decimals": 6}
                        }
                    ]
                },
                "transaction": {"signatures": [test_sig]}
            },
            "id": 1
        }
        mock_post.return_value = mock_resp

        ok, msg = x402_verifier._verify_solana_onchain_tx(test_sig, required_amount_usdc=0.05)
        assert ok is True
        assert msg is not None and ("tx:" in msg or "Solana" in msg)

        # 3. Anti-replay test: same signature must now be rejected
        ok_replay, replay_msg = x402_verifier._verify_solana_onchain_tx(test_sig, required_amount_usdc=0.05)
        assert ok_replay is False
        assert replay_msg is not None and ("already been redeemed" in replay_msg or "Replay attack" in replay_msg)


def test_solana_truth_attestation_sync_and_async():
    """Verify Security Gate Client generates valid Ed25519 truth attestation for Solana."""
    fake_solana_attest = {
        "status": "ATTESTED",
        "domain": "CONFLICT_MINERALS",
        "domain_id": 4,
        "oracle_pubkey": "774hK5wmk5pStvsh5DH46pYPYYD3ro7tMfz1ASxcbiTK",
        "signature_scheme": "Ed25519",
        "signature": "3a" * 64,
        "confidence_score": 0.999,
        "chain_id": 501,
        "chain": "solana",
        "latency_ms": 38.5
    }

    # Test sync client
    with patch.object(security_gate_client._client, "post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = fake_solana_attest
        mock_post.return_value = mock_resp

        res = security_gate_client.request_solana_truth_attestation(
            domain="CONFLICT_MINERALS",
            domain_id=4,
            query_payload={"smelter_id": "CID002991", "mineral": "cobalt"},
            confidence_score=0.999
        )

        assert res["status"] == "ATTESTED"
        assert res["signature_scheme"] == "Ed25519"
        assert res["chain_id"] == 501
        assert res["domain"] == "CONFLICT_MINERALS"

    # Test standalone fallback generation
    fallback = security_gate_client._create_local_solana_attestation(
        job_id_hex="job_minerals_001",
        domain=4,
        truth_hash_hex="11223344",
        recipients_hash_hex="55667788",
        validity_seconds=3600
    )
    assert fallback["chain_id"] == 501
    assert fallback["signature_scheme"] == "Ed25519"
    assert len(fallback["signature"]) == 128


@pytest.mark.asyncio
async def test_solana_universal_escrow_settlement():
    """Verify sub-second universal escrow settlement and 99.8% / 0.1% / 0.1% split on Solana."""
    fake_settle_response = {
        "status": "SETTLED",
        "settlement_rail": "SOLANA_MAINNET",
        "chain_id": 501,
        "deal_id": "DEAL-SOL-2026-X1",
        "gross_amount_usdc": 1000.0,
        "settlement_breakdown": {
            "seller_agent_net_usdc": 998.0,
            "minerals_oracle_fee_usdc": 1.0,
            "security_gate_staking_fee_usdc": 1.0,
            "seller_agent_pubkey": "SellerAgent11111111111111111111111111111111",
            "minerals_oracle_treasury": "411ksMz9RHYVtVMe6RUUErzZYtrU9zzvkgzswKbqx9qp",
            "security_gate_staking_pool": "774hK5wmk5pStvsh5DH46pYPYYD3ro7tMfz1ASxcbiTK"
        },
        "solana_tx_signature": "5VerBQQuJYvHiU1fXb6Vd99Q3aP3h6k6yqgXfCjE288jC2jVn8P6wM7g8k8R7K8L2wM4pQ6k6yqgXfCjE288jC2",
        "latency_ms": 395.0,
        "sub_second_finality": True
    }

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = fake_settle_response
        mock_post.return_value = mock_resp

        res = await security_gate_client.settle_solana_universal_escrow_async(
            deal_id="DEAL-SOL-2026-X1",
            buyer_agent_pubkey="BuyerAgent111111111111111111111111111111111",
            seller_agent_pubkey="SellerAgent11111111111111111111111111111111",
            gross_amount_usdc=1000.0,
            oracle_domain="CONFLICT_MINERALS",
            oracle_id=4
        )

        assert res["status"] == "SETTLED"
        assert res["settlement_rail"] == "SOLANA_MAINNET"
        assert res["sub_second_finality"] is True
        assert res["settlement_breakdown"]["seller_agent_net_usdc"] == 998.0
        assert res["settlement_breakdown"]["minerals_oracle_fee_usdc"] == 1.0


def test_fastapi_security_gate_status_endpoint():
    """Verify GET /api/v1/oracle/security-gate/status returns Solana Mainnet configuration."""
    response = client.get("/api/v1/oracle/security-gate/status")
    assert response.status_code == 200
    data = response.json()
    assert "Solana Mainnet (501)" in data["supported_networks"]
    assert "solana_config" in data
    assert data["solana_config"]["chain_id"] == 501
    assert "411ksMz9RHYVtVMe6RUUErzZYtrU9zzvkgzswKbqx9qp" in data["solana_config"]["treasury_pubkey"]


def test_fastapi_solana_attest_endpoint():
    """Verify POST /api/v1/escrow/universal/solana/attest endpoint executes cleanly."""
    payload = {
        "domain": "CONFLICT_MINERALS",
        "domain_id": 4,
        "query_payload": {
            "smelter_id": "CID002991",
            "mineral": "cobalt",
            "provenance_status": "VERIFIED"
        },
        "client_identity": "411ksMz9RHYVtVMe6RUUErzZYtrU9zzvkgzswKbqx9qp",
        "confidence_score": 0.999
    }

    response = client.post("/api/v1/escrow/universal/solana/attest", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("ATTESTED", "ISSUED", "VERIFIED")
    assert data["chain_id"] == 501
    assert data["signature_scheme"] == "Ed25519"
    assert "signature" in data


def test_fastapi_solana_settle_endpoint():
    """Verify POST /api/v1/escrow/universal/settle-solana endpoint executes sub-second split settlement."""
    payload = {
        "deal_id": "DEAL-SOLANA-MINERAL-001",
        "buyer_agent_pubkey": "BuyerAgent111111111111111111111111111111111",
        "seller_agent_pubkey": "SellerAgent11111111111111111111111111111111",
        "gross_amount_usdc": 500.0,
        "oracle_domain": "CONFLICT_MINERALS",
        "oracle_id": 4
    }

    response = client.post("/api/v1/escrow/universal/settle-solana", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "SETTLED"
    assert data["settlement_rail"] == "SOLANA_MAINNET"
    assert data["chain_id"] == 501
    assert data["settlement_breakdown"]["seller_agent_net_usdc"] == 499.0
    assert data["settlement_breakdown"]["minerals_oracle_fee_usdc"] == 0.50
    assert data["settlement_breakdown"]["security_gate_staking_fee_usdc"] == 0.50


def test_solana_spl_usdc_balance_diff_verification():
    """Verify SPL USDC balance difference (preTokenBalances vs postTokenBalances) parsing."""
    import secrets
    rand_chars = "".join(secrets.choice("123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz") for _ in range(34))
    test_sig = "5VerBQQuJYvHiU1fXb6Vd99Q3aP3h6k6yqgXfCjE288jC2jVn8P6wM" + rand_chars
    treasury_sol = "411ksMz9RHYVtVMe6RUUErzZYtrU9zzvkgzswKbqx9qp"
    usdc_mint = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"

    # Case A: Treasury balance increased by 0.05 USDC -> PASS
    with patch("httpx.Client.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "jsonrpc": "2.0",
            "result": {
                "slot": 240000000,
                "meta": {
                    "err": None,
                    "preTokenBalances": [
                        {
                            "accountIndex": 1,
                            "mint": usdc_mint,
                            "owner": treasury_sol,
                            "uiTokenAmount": {"uiAmount": 10.0, "amount": "10000000", "decimals": 6}
                        }
                    ],
                    "postTokenBalances": [
                        {
                            "accountIndex": 1,
                            "mint": usdc_mint,
                            "owner": treasury_sol,
                            "uiTokenAmount": {"uiAmount": 10.05, "amount": "10050000", "decimals": 6}
                        }
                    ]
                },
                "transaction": {"signatures": [test_sig]}
            },
            "id": 1
        }
        mock_post.return_value = mock_resp

        ok, msg = x402_verifier._verify_solana_onchain_tx(test_sig, required_amount_usdc=0.05)
        assert ok is True
        assert msg is not None and "tx:" in msg

    # Case B: Insufficient amount transferred -> REJECT
    rand_chars2 = "".join(secrets.choice("123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz") for _ in range(34))
    test_sig2 = "5VerBQQuJYvHiU1fXb6Vd99Q3aP3h6k6yqgXfCjE288jC2jVn8P6wM" + rand_chars2
    with patch("httpx.Client.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "jsonrpc": "2.0",
            "result": {
                "slot": 240000000,
                "meta": {
                    "err": None,
                    "preTokenBalances": [
                        {
                            "accountIndex": 1,
                            "mint": usdc_mint,
                            "owner": treasury_sol,
                            "uiTokenAmount": {"uiAmount": 10.0, "amount": "10000000", "decimals": 6}
                        }
                    ],
                    "postTokenBalances": [
                        {
                            "accountIndex": 1,
                            "mint": usdc_mint,
                            "owner": treasury_sol,
                            "uiTokenAmount": {"uiAmount": 10.001, "amount": "10001000", "decimals": 6}
                        }
                    ]
                },
                "transaction": {"signatures": [test_sig2]}
            },
            "id": 1
        }
        mock_post.return_value = mock_resp

        ok, msg = x402_verifier._verify_solana_onchain_tx(test_sig2, required_amount_usdc=0.05)
        assert ok is False
        assert msg is not None and "No matching SPL USDC transfer" in msg


def test_multi_rpc_failover_resilience():
    """Verify Multi-RPC automatic failover when primary RPC is down or rate-limited."""
    import secrets
    rand_chars = "".join(secrets.choice("123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz") for _ in range(34))
    test_sig = "5VerBQQuJYvHiU1fXb6Vd99Q3aP3h6k6yqgXfCjE288jC2jVn8P6wM" + rand_chars

    # 1st call fails (HTTP 429), 2nd call succeeds (HTTP 200)
    mock_resp_fail = MagicMock()
    mock_resp_fail.status_code = 429

    treasury_sol = "411ksMz9RHYVtVMe6RUUErzZYtrU9zzvkgzswKbqx9qp"
    usdc_mint = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
    mock_resp_ok = MagicMock()
    mock_resp_ok.status_code = 200
    mock_resp_ok.json.return_value = {
        "jsonrpc": "2.0",
        "result": {
            "slot": 240000001,
            "meta": {
                "err": None,
                "preTokenBalances": [
                    {
                        "accountIndex": 1,
                        "mint": usdc_mint,
                        "owner": treasury_sol,
                        "uiTokenAmount": {"uiAmount": 20.0, "amount": "20000000", "decimals": 6}
                    }
                ],
                "postTokenBalances": [
                    {
                        "accountIndex": 1,
                        "mint": usdc_mint,
                        "owner": treasury_sol,
                        "uiTokenAmount": {"uiAmount": 20.05, "amount": "20050000", "decimals": 6}
                    }
                ]
            },
            "transaction": {"signatures": [test_sig]}
        },
        "id": 1
    }

    with patch("httpx.Client.post", side_effect=[mock_resp_fail, mock_resp_ok]):
        ok, msg = x402_verifier._verify_solana_onchain_tx(test_sig, required_amount_usdc=0.05)
        assert ok is True
        assert msg is not None and "tx:" in msg


def test_solana_security_invariants_reject_empty_tokens_and_third_party():
    """Security Invariant: Non-token transactions and third-party transfers MUST be rejected."""
    import secrets
    rand_chars = "".join(secrets.choice("123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz") for _ in range(34))
    test_sig = "5VerBQQuJYvHiU1fXb6Vd99Q3aP3h6k6yqgXfCjE288jC2jVn8P6wM" + rand_chars

    # 1. Non-token transaction (e.g. 0 SOL transfer or memo) with empty token balances -> MUST BE REJECTED
    with patch("httpx.Client.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "jsonrpc": "2.0",
            "result": {
                "slot": 240000000,
                "meta": {"err": None, "preTokenBalances": [], "postTokenBalances": []},
                "transaction": {"signatures": [test_sig]}
            },
            "id": 1
        }
        mock_post.return_value = mock_resp
        ok, reason = x402_verifier._verify_solana_onchain_tx(test_sig, required_amount_usdc=0.05)
        assert ok is False
        assert "No matching SPL USDC transfer" in str(reason)

    # 2. Transfer to third party (attacker's friend) -> MUST BE REJECTED
    rand_chars2 = "".join(secrets.choice("123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz") for _ in range(34))
    test_sig2 = "5VerBQQuJYvHiU1fXb6Vd99Q3aP3h6k6yqgXfCjE288jC2jVn8P6wM" + rand_chars2
    attacker_friend = "SomeThirdPartyWallet11111111111111111111111"
    usdc_mint = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"

    with patch("httpx.Client.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "jsonrpc": "2.0",
            "result": {
                "slot": 240000000,
                "meta": {
                    "err": None,
                    "preTokenBalances": [{"accountIndex": 2, "mint": usdc_mint, "owner": attacker_friend, "uiTokenAmount": {"uiAmount": 0.0}}],
                    "postTokenBalances": [{"accountIndex": 2, "mint": usdc_mint, "owner": attacker_friend, "uiTokenAmount": {"uiAmount": 10.0}}]
                },
                "transaction": {
                    "signatures": [test_sig2],
                    "message": {
                        "instructions": [
                            {
                                "parsed": {
                                    "type": "transfer",
                                    "info": {
                                        "amount": "10000000",
                                        "authority": "AttackerWallet",
                                        "destination": "AttackerFriendTokenAccount",
                                        "source": "AttackerTokenAccount"
                                    }
                                }
                            }
                        ]
                    }
                }
            },
            "id": 1
        }
        mock_post.return_value = mock_resp
        ok2, reason2 = x402_verifier._verify_solana_onchain_tx(test_sig2, required_amount_usdc=0.05)
        assert ok2 is False
        assert "No matching SPL USDC transfer" in str(reason2)


def test_multichain_deployed_registry_strict_parity():
    """Verify that multi_chain CHAIN_REGISTRY strictly matches deployed contracts and IDLs."""
    from app.multi_chain import CHAIN_REGISTRY, SupportedChain

    # 1. Base Contracts
    base_cfg = CHAIN_REGISTRY[SupportedChain.BASE.value]
    assert base_cfg.payment_vault_address == "0x8ACafCEce0B1BFE140e75614b90FD1307b6f389d"
    assert base_cfg.oracle_consumer_address == "0xe43a9C368808B2dfF139D27789C40A3C8F2282cF"

    # 2. Arbitrum Contracts
    arb_cfg = CHAIN_REGISTRY[SupportedChain.ARBITRUM.value]
    assert arb_cfg.payment_vault_address == "0x8ACafCEce0B1BFE140e75614b90FD1307b6f389d"
    assert arb_cfg.oracle_consumer_address == "0xe43a9C368808B2dfF139D27789C40A3C8F2282cF"

    # 3. Solana Contracts
    sol_cfg = CHAIN_REGISTRY[SupportedChain.SOLANA.value]
    assert sol_cfg.payment_vault_address == "7oZ16YaazQzN6z5uA1nAZWD9oGUDXyvHwXGJLFYyWi3y"
    assert sol_cfg.oracle_consumer_address == "21ZR1QCyAbNrRLs1iWEkdbNsfCFdJcy6ip9R2JxDbkTL"


def test_vault_manager_evm_and_solana_address_normalization():
    """Verify VaultManager handles uppercase 0X, standard 0x, and Solana Base58 pubkeys robustly."""
    from app.vault_manager import vault_manager

    # 1. Lowercase vs Uppercase EVM address normalization
    raw_evm = "0x" + "a" * 40
    raw_evm_upper = "0X" + "a" * 40
    acc1, _ = vault_manager.register_agent_onboarding("TestAgentEvm", agent_address=raw_evm)
    acc2, _ = vault_manager.register_agent_onboarding("TestAgentEvmUpper", agent_address=raw_evm_upper)
    assert acc1.agent_address == acc2.agent_address

    # 2. Solana Base58 pubkey onboarding and retrieval
    sol_addr = "411ksMz9RHYVtVMe6RUUErzZYtrU9zzvkgzswKbqx9qp"
    acc_sol, s_key = vault_manager.register_agent_onboarding("TestAgentSol", agent_address=sol_addr)
    assert acc_sol.agent_address == sol_addr

    retrieved = vault_manager.get_account_by_address(sol_addr)
    assert retrieved is not None
    assert retrieved.agent_address == sol_addr

    # 3. try_deduct using normalized address directly
    ok, addr, bal = vault_manager.try_deduct(sol_addr, 0.005)
    assert ok is True
    assert addr == sol_addr


def test_evm_tx_format_not_falsely_routed_to_solana():
    """Verify that EVM transactions without 0x prefix or invalid length fail with EVM error, not Solana error."""
    # 64-char hex without 0x on polygon
    bad_evm_hex = "a" * 64
    ok, err = x402_verifier.verify_onchain_tx(bad_evm_hex, chain_name="polygon")
    assert ok is False
    assert "Invalid EVM transaction hash format" in str(err)
    assert "Solana" not in str(err)

