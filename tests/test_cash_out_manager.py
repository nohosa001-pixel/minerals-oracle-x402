"""
Unit and Integration Tests for Safe Cash-Out (Liquidation) & Capital Efficiency Manager.
"""

import json
import os
import shutil
import tempfile
import pytest
from app.cash_out_manager import CashOutManager, cash_out_manager
from app.telegram_bot import telegram_bot



@pytest.fixture
def temp_manager_env():
    """Creates an isolated temporary state file and log directory."""
    temp_dir = tempfile.mkdtemp()
    state_file = os.path.join(temp_dir, "bot_state.json")
    
    initial_state = {
        "total_capital_usd": 155146.34,
        "safe_reserve_vault_usd": 149646.34,
        "trade_size_usd": 2500.0,
        "cumulative_net_pnl": 376414.97,
        "total_trades_executed": 602,
        "active_positions_count": 3,
        "active_positions": {},
    }
    with open(state_file, "w", encoding="utf-8") as f:
        json.dump(initial_state, f)

    manager = CashOutManager(
        state_file=state_file,
        log_dir=temp_dir,
        min_working_capital_floor=20000.0,
        default_fx_rate=1350.0,
    )

    yield manager, state_file, temp_dir

    shutil.rmtree(temp_dir, ignore_errors=True)


def test_liquidation_status_calculation(temp_manager_env):
    manager, state_file, _ = temp_manager_env
    status = manager.get_liquidation_status(fx_rate=1350.0)

    assert status["safe_reserve_vault_usd"] == 149646.34
    assert status["safe_reserve_vault_krw"] == round(149646.34 * 1350.0, 0)
    assert status["working_capital_usd"] == 155146.34
    assert status["min_working_capital_floor_usd"] == 20000.0
    # Available from working pool: 155146.34 - 20000 = 135146.34
    assert status["available_from_working_pool_usd"] == 135146.34
    # Total available: 149646.34 + 135146.34 = 284792.68
    assert status["total_available_for_cashout_usd"] == 284792.68
    assert status["est_annual_tax_krw"] > 0


def test_cash_out_bounds_and_rejection(temp_manager_env):
    manager, _, _ = temp_manager_env

    # 1. Reject negative or 0
    ok, msg, req = manager.request_cash_out(0.0)
    assert not ok
    assert req is None

    # 2. Reject excessive amount from safe vault
    ok, msg, req = manager.request_cash_out(200000.0, source_pool="SAFE_VAULT")
    assert not ok
    assert "초과합니다" in msg


def test_two_step_cashout_lifecycle(temp_manager_env):
    manager, state_file, temp_dir = temp_manager_env

    # Step 1: Request $50,000 withdrawal from Safe Vault
    ok, msg, req = manager.request_cash_out(
        amount_usd=50000.0,
        target_destination="SHINHAN_BANK_MAIN_ACCOUNT",
        source_pool="SAFE_VAULT",
        fx_rate=1350.0,
        memo="Q3 Profit Distribution",
    )
    assert ok
    assert req is not None
    req_id = req["request_id"]
    token = req["token"]
    assert len(token) == 6
    assert req["amount_krw"] == 67500000.0

    # Step 2: Confirm with wrong token -> should fail
    ok_fail, msg_fail, _ = manager.confirm_cash_out(req_id, "999999")
    assert not ok_fail
    assert "일치하지 않습니다" in msg_fail

    # Step 3: Confirm with valid token
    ok_succ, msg_succ, res = manager.confirm_cash_out(req_id, token, execute_actual=True)
    assert ok_succ
    assert res["remaining_vault_usd"] == round(149646.34 - 50000.0, 2)
    assert res["remaining_working_capital_usd"] == 155146.34

    # Verify updated bot_state.json
    with open(state_file, "r", encoding="utf-8") as f:
        new_state = json.load(f)
    assert new_state["safe_reserve_vault_usd"] == 99646.34

    # Verify journal CSV exists and has 1 record
    journal_path = os.path.join(temp_dir, "cashout_journal.csv")
    assert os.path.exists(journal_path)
    with open(journal_path, "r", encoding="utf-8-sig") as f:
        lines = f.readlines()
    assert len(lines) == 2  # Header + 1 record
    assert "SHINHAN_BANK_MAIN_ACCOUNT" in lines[1]
    assert "50000.00" in lines[1]


def test_telegram_cashout_commands():
    bot_ctx = {
        "is_paused": False,
        "cumulative_pnl": 376414.97,
        "total_trades": 602,
        "active_positions_count": 0,
        "total_capital": 155146.34,
        "safe_vault_total": 149646.34,
        "locked_margin": 0.0,
        "dry_run": True,
    }

    # Test /cashout_status
    resp_status = telegram_bot.handle_command("/cashout_status", bot_ctx)
    assert "안전 현금화(Cash-Out)" in resp_status
    assert "안전 금고(Safe Vault)" in resp_status

    # Test /cashout_request invalid
    resp_err = telegram_bot.handle_command("/cashout_request", bot_ctx)
    assert "형식 오류" in resp_err

    # Test /cashout_request valid
    cash_out_manager.safe_reserve_vault_usd = 20000.0
    resp_req = telegram_bot.handle_command("/cashout_request 10000", bot_ctx)
    assert "안전 현금화 2단계 승인 대기" in resp_req
    assert "승인 토큰" in resp_req



