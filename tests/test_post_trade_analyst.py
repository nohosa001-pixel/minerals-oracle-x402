import pytest
import os
import shutil
from app.post_trade_analyst import PostTradeAnalyst

TEST_REPORTS_DIR = "logs/test_audit_reports"


@pytest.fixture
def clean_analyst():
    if os.path.exists(TEST_REPORTS_DIR):
        shutil.rmtree(TEST_REPORTS_DIR)
    analyst = PostTradeAnalyst(reports_dir=TEST_REPORTS_DIR)
    yield analyst
    if os.path.exists(TEST_REPORTS_DIR):
        shutil.rmtree(TEST_REPORTS_DIR)


def test_evaluate_trade_grade_a(clean_analyst):
    # Winning trade satisfying 4x commission hurdle and low slippage
    trade = {
        "trade_id": "TEST-CU-001",
        "symbol": "Cu",
        "entry_price": 6.6500,
        "exit_price": 6.6700,
        "gross_profit_usd": 15.0,
        "commission_usd": 3.0,
        "net_pnl_usd": 12.0,
        "holding_sec": 420.0,
        "action": "PROFIT_TARGET_MET",
        "kis_account": "10061681-08",
        "kis_order_id": "OD999",
    }
    res = clean_analyst.evaluate_trade(
        trade, target_entry_price=6.6500, target_exit_price=6.6700
    )

    assert res["grade"] == "A"
    assert res["hurdle_passed"] is True
    assert res["commission_multiple"] == 5.0
    assert res["entry_slippage_bps"] == 0.0
    assert os.path.exists(os.path.join(TEST_REPORTS_DIR, "audit_TEST-CU-001.md"))


def test_evaluate_trade_circuit_breaker(clean_analyst):
    # Loss trade due to defensive circuit breaker
    trade = {
        "trade_id": "TEST-CU-002",
        "symbol": "Cu",
        "entry_price": 6.6700,
        "exit_price": 6.6400,
        "gross_profit_usd": -12.0,
        "commission_usd": 3.0,
        "net_pnl_usd": -15.0,
        "holding_sec": 300.0,
        "action": "CIRCUIT_BREAKER_TRIGGERED",
        "kis_account": "10061681-08",
    }
    res = clean_analyst.evaluate_trade(trade)

    assert res["grade"] == "C+"
    assert "손실 브레이크" in res["critique"]
    assert res["hurdle_passed"] is False


def test_summary_statistics(clean_analyst):
    # Trade 1: Win
    clean_analyst.evaluate_trade({
        "trade_id": "T1",
        "symbol": "Cu",
        "entry_price": 6.65,
        "exit_price": 6.68,
        "gross_profit_usd": 20.0,
        "commission_usd": 3.0,
        "net_pnl_usd": 17.0,
    })
    # Trade 2: Loss
    clean_analyst.evaluate_trade({
        "trade_id": "T2",
        "symbol": "Cu",
        "entry_price": 6.68,
        "exit_price": 6.66,
        "gross_profit_usd": -10.0,
        "commission_usd": 3.0,
        "net_pnl_usd": -13.0,
    })

    stats = clean_analyst.get_summary_statistics()
    assert stats["total_trades"] == 2
    assert stats["win_count"] == 1
    assert stats["loss_count"] == 1
    assert stats["win_rate_pct"] == 50.0
    assert stats["profit_factor"] == 1.31
    assert stats["total_net_pnl_usd"] == 4.0


def test_telegram_audit_message(clean_analyst):
    audit = {
        "trade_id": "T3",
        "symbol": "Cu",
        "grade": "A",
        "net_pnl_usd": 15.5,
        "commission_multiple": 5.2,
        "holding_time_formatted": "5분 30초",
        "entry_slippage_bps": 0.5,
        "exit_slippage_bps": -0.2,
        "critique": "완벽한 원칙 준수",
    }
    msg = clean_analyst.generate_telegram_audit_message(audit)
    assert "[사후 매매 학습 보고서]" in msg
    assert "Cu" in msg
    assert "+15.50" in msg
