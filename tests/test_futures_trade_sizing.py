import pytest
from app.kis_client import (
    kis_client,
    TradeMode,
    TradeSizingMode,
    FUTURES_CONTRACT_SPECS,
)
from app.cloud_bot_worker import cloud_bot_worker


def test_futures_contract_specs_integrity():
    """Verifies that all supported commodity futures and ETFs have valid contract specifications."""
    symbols = ["Cu", "Ag", "Pt", "Li", "NdDy"]
    for sym in symbols:
        assert sym in FUTURES_CONTRACT_SPECS, f"Missing contract spec for {sym}"
        spec = FUTURES_CONTRACT_SPECS[sym]
        assert "micro" in spec and "standard" in spec and "etf" in spec
        assert spec["micro"]["initial_margin_usd"] > 0
        assert spec["standard"]["initial_margin_usd"] > 0
        assert spec["micro"]["contract_size"] > 0
        assert spec["standard"]["contract_size"] > 0
        assert spec["etf"]["ticker"] is not None


def test_trade_sizing_futures_micro_fixed_lots():
    """Tests fixed lot sizing for Micro Futures contracts."""
    res = kis_client.calculate_order_sizing(
        symbol="Cu",
        mode=TradeMode.FUTURES_MICRO,
        sizing_mode=TradeSizingMode.FIXED_LOTS,
        capital_usd=2000.0,
        fixed_lots=2,
        spread_bps=120.0,
        unit_price=15000.0,
    )
    assert res["trade_mode"] == "FUTURES_MICRO"
    assert res["instrument_type"] == "OVERSEAS_FUTURES"
    assert res["ticker"] == "MHG"
    assert res["quantity"] == 2
    assert res["unit_label"] == "lots"
    assert res["contract_multiplier"] == 2500.0
    assert res["initial_margin_usd"] == 950.0 * 2
    assert "08" in res["account_no"]


def test_trade_sizing_futures_standard_capital_based():
    """Tests capital-based sizing for Standard Futures contracts."""
    res = kis_client.calculate_order_sizing(
        symbol="Ag",
        mode=TradeMode.FUTURES_STANDARD,
        sizing_mode=TradeSizingMode.CAPITAL_BASED,
        capital_usd=25000.0,
        fixed_lots=1,
        spread_bps=80.0,
        margin_buffer_pct=20.0,
    )
    assert res["trade_mode"] == "FUTURES_STANDARD"
    assert res["ticker"] == "SI"
    assert res["contract_multiplier"] == 5000.0
    assert res["quantity"] >= 2  # $25,000 / ($9,000 * 1.2 = $10,800) = 2 lots
    assert "08" in res["account_no"]


def test_trade_sizing_etf_mode():
    """Tests ETF stock trade sizing mode."""
    res = kis_client.calculate_order_sizing(
        symbol="Pt",
        mode=TradeMode.ETF,
        sizing_mode=TradeSizingMode.CAPITAL_BASED,
        capital_usd=1000.0,
    )
    assert res["trade_mode"] == "ETF"
    assert res["instrument_type"] == "OVERSEAS_ETF"
    assert res["ticker"] == "PPLT"
    assert res["quantity"] >= 1
    assert res["unit_label"] == "shares"
    assert "01" in res["account_no"]


def test_trade_sizing_auto_mode_switch():
    """Tests AUTO mode selecting Micro Futures when capital is sufficient and ETF when capital is low."""
    # 1. Low capital -> selects ETF
    res_low = kis_client.calculate_order_sizing(
        symbol="Cu",
        mode=TradeMode.AUTO,
        capital_usd=300.0,
    )
    assert res_low["trade_mode"] == "ETF"
    assert res_low["ticker"] == "CPER"

    # 2. Sufficient capital -> selects Micro Futures
    res_high = kis_client.calculate_order_sizing(
        symbol="Cu",
        mode=TradeMode.AUTO,
        capital_usd=2000.0,
    )
    assert res_high["trade_mode"] == "FUTURES_MICRO"
    assert res_high["ticker"] == "MHG"


def test_trade_sizing_dynamic_kelly():
    """Tests Dynamic Kelly fraction booster for large basis spreads."""
    res_normal = kis_client.calculate_order_sizing(
        symbol="Li",
        mode=TradeMode.FUTURES_MICRO,
        sizing_mode=TradeSizingMode.DYNAMIC_KELLY,
        capital_usd=3000.0,
        spread_bps=100.0,
    )
    res_super = kis_client.calculate_order_sizing(
        symbol="Li",
        mode=TradeMode.FUTURES_MICRO,
        sizing_mode=TradeSizingMode.DYNAMIC_KELLY,
        capital_usd=3000.0,
        spread_bps=300.0,
    )
    assert res_super["quantity"] >= res_normal["quantity"]


def test_kis_auto_hedge_order_execution():
    """Tests simulated order dispatching for both futures and ETF orders."""
    # 1. Futures order dispatch
    futures_plan = kis_client.calculate_order_sizing("Cu", mode=TradeMode.FUTURES_MICRO, capital_usd=1500.0)
    res_f = kis_client.execute_auto_hedge_order(
        symbol="Cu",
        spread_bps=140.0,
        net_margin_usd=110.0,
        direction="Long LME -> Short COMEX",
        sizing_plan=futures_plan,
        dry_run=True,
    )
    assert res_f["status"] == "DRY_RUN_UNEXECUTED"
    assert "FUTURES" in res_f["instrument_type"]
    assert res_f["ticker"] == "MHG"

    # 2. ETF order dispatch
    etf_plan = kis_client.calculate_order_sizing("Ag", mode=TradeMode.ETF, capital_usd=200.0)
    res_e = kis_client.execute_auto_hedge_order(
        symbol="Ag",
        spread_bps=80.0,
        net_margin_usd=0.45,
        direction="Buy (Open Hedge)",
        sizing_plan=etf_plan,
        dry_run=True,
    )
    assert res_e["status"] == "DRY_RUN_UNEXECUTED"
    assert res_e["instrument_type"] == "OVERSEAS_ETF"
    assert res_e["ticker"] == "SLV"


def test_cloud_bot_worker_config_update():
    """Tests dynamic config update in cloud arbitrage worker."""
    cfg = cloud_bot_worker.get_config()
    assert "trade_mode" in cfg
    assert "supported_contract_specs" in cfg

    updated = cloud_bot_worker.update_config({
        "trade_mode": "FUTURES_MICRO",
        "sizing_mode": "DYNAMIC_KELLY",
        "fixed_lots": 3,
        "target_commodity": "ALL",
        "total_capital_usd": 2500.0,
    })
    assert updated["trade_mode"] == "FUTURES_MICRO"
    assert updated["sizing_mode"] == "DYNAMIC_KELLY"
    assert updated["fixed_lots"] == 3
    assert updated["total_capital_usd"] == 2500.0
