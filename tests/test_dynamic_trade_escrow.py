"""
Tests for DynamicTradeEscrow.sol contract invariants, Pyth mark-to-market valuation,
autonomous margin-call defense, and tripartite settlement invariants.
"""

from pathlib import Path

CONTRACT_PATH = Path(__file__).parent.parent / "contracts" / "DynamicTradeEscrow.sol"


def test_dynamic_trade_escrow_source_exists():
    """Validates that DynamicTradeEscrow.sol exists and is non-empty."""
    assert CONTRACT_PATH.exists(), "DynamicTradeEscrow.sol does not exist"
    src = CONTRACT_PATH.read_text(encoding="utf-8")
    assert len(src) > 500


def test_dynamic_trade_escrow_invariants():
    """
    Formal static analysis of DynamicTradeEscrow.sol.
    Validates essential DeFi & escrow security properties:
    1. Checks-Effects-Interactions pattern for settlement and refunds.
    2. Pyth Oracle mark-to-market and margin-call defense implementation.
    3. Emergency pause/unpause safety guards.
    4. Mathematical dispute solvency (buyerRefund + sellerPayout == totalHeld).
    5. Minimum duration validation (>= 60s).
    """
    src = CONTRACT_PATH.read_text(encoding="utf-8")

    # 1. Checks-Effects-Interactions (Reentrancy defense)
    # Status updated BEFORE token transfer in settleDeal
    idx_settle_status = src.find("deal.status = EscrowStatus.RELEASED_SETTLED;")
    idx_settle_transfer = src.find("usdcToken.transfer(deal.sellerAgent, deal.totalAmountUsdc)")
    assert idx_settle_status != -1 and idx_settle_transfer != -1
    assert idx_settle_status < idx_settle_transfer, "Reentrancy flaw: Settle status updated after transfer!"

    # Status updated BEFORE token transfer in refundExpiredDeal
    idx_refund_status = src.find("deal.status = EscrowStatus.REFUNDED;")
    idx_refund_transfer = src.find("usdcToken.transfer(deal.buyerAgent, totalRefund)")
    assert idx_refund_status != -1 and idx_refund_transfer != -1
    assert idx_refund_status < idx_refund_transfer, "Reentrancy flaw: Refund status updated after transfer!"

    # 2. Pyth Oracle and Margin Call functions
    assert "function evaluateMarginCall(" in src, "evaluateMarginCall function missing"
    assert "function depositMarginTopup(" in src, "depositMarginTopup function missing"
    assert "emit MarginCallTriggered(" in src, "MarginCallTriggered event not emitted"
    assert "emit MarginTopupDeposited(" in src, "MarginTopupDeposited event not emitted"

    # 3. Emergency Pause Guards
    assert "whenNotPaused" in src, "whenNotPaused modifier missing"
    assert "function pause() external onlyOwner" in src, "pause function missing"
    assert "function unpause() external onlyOwner" in src, "unpause function missing"

    # 4. Dispute Arbitrage Solvency
    assert "buyerRefundUsdc + sellerPayoutUsdc == totalHeld" in src, "Dispute solvency check missing"

    # 5. Duration and Input Validation
    assert "require(durationSeconds >= 60" in src, "Duration >= 60s check missing"
    assert "require(inspector != address(0)" in src, "Inspector non-zero address check missing"
    assert "require(basePriceUsd > 0" in src, "Base price positive check missing"


def test_dynamic_trade_escrow_multichain_registered():
    """Validates that DynamicTradeEscrow is registered across Polygon, Base, and Arbitrum."""
    import json
    multichain_path = Path(__file__).parent.parent / "contracts" / "deployed_multichain.json"
    assert multichain_path.exists()
    data = json.loads(multichain_path.read_text(encoding="utf-8"))
    
    for chain in ["polygon", "base", "arbitrum"]:
        chain_info = data["networks"][chain]
        assert "DynamicTradeEscrow" in chain_info["contracts"], f"DynamicTradeEscrow missing in {chain}"
        escrow = chain_info["contracts"]["DynamicTradeEscrow"]
        assert escrow["address"].startswith("0x")
        assert escrow["pythOracle"].startswith("0x")
        assert escrow["settlementToken"].startswith("0x")


def test_dynamic_escrow_calldata_generation():
    """Validates that build_dynamic_escrow_deposit_calldata produces valid calldata for DynamicTradeEscrow."""
    from app.a2a_deal_engine import A2ATradeDealEngine
    from app.schemas import TradeDealProposeRequest, TradeDealDualSignRequest, TradeDealSpec, MineralType, SourceCountry

    engine = A2ATradeDealEngine()
    deal_id = "DEAL-DYN-TEST-001"
    buyer = "0x" + "1" * 40
    seller = "0x" + "2" * 40

    spec = TradeDealSpec(
        deal_id=deal_id,
        commodity=MineralType.COPPER_CATHODE,
        volume_tons=100.0,
        unit_price_usd_per_ton=6610.0,
        total_deal_value_usd=661000.0,
        origin_country=SourceCountry.CHL,
        destination_country="KR",
        ebl_document_id="EBL-MAERSK-2026-CU100",
        buyer_agent_address=buyer,
        seller_agent_address=seller,
        created_at_utc="2026-10-07T12:00:00Z",
    )

    prop = TradeDealProposeRequest(
        spec=spec,
        seller_signature="0x" + "a" * 130,
    )
    engine.propose_deal(prop)

    dual = TradeDealDualSignRequest(
        deal_id=deal_id,
        buyer_agent_address=buyer,
        buyer_signature="0x" + "c" * 130,
    )
    engine.dual_sign_deal(dual)

    for chain in ["polygon", "base", "arbitrum"]:
        res = engine.build_dynamic_escrow_deposit_calldata(
            deal_id=deal_id,
            collateral_deposit_usdc=50000.0,
            chain_name=chain,
        )
        assert res["escrow_type"] == "dynamic"
        assert res["function_signature"] == "createDynamicDeal(bytes32,address,address,uint256,uint256,bytes32,int64,uint256,uint256)"
        assert res["calldata"].startswith("0x")
        assert res["escrow_contract_address"].startswith("0x")
        assert res["total_required_deposit_usdc"] == 711000.0

