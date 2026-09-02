"""
Unit Tests for Interactive Telegram Bot Commands (/status, /balance, /positions, /pause, /resume).
"""

from app.telegram_bot import telegram_bot


def test_telegram_commands_handling():
    bot_ctx = {
        "is_paused": False,
        "cumulative_pnl": 1250.75,
        "total_trades": 18,
        "active_positions_count": 2,
        "active_positions": {
            "Cu": {
                "entry_price": 15000.0,
                "cur_price": 15120.0,
                "quantity": 1,
                "margin_usd": 950.0,
                "entry_bps": 120.0,
                "instrument_type": "OVERSEAS_FUTURES",
            }
        },
        "total_capital": 5500.0,
        "safe_vault_total": 600.0,
        "locked_margin": 950.0,
        "dry_run": True,
    }

    # 1. /status command (Under simulation/learning, profit is strictly ZERO as requested by user)
    status_reply = telegram_bot.handle_command("/status", bot_ctx)
    assert "실시간 봇 가동 상태 리포트" in status_reply
    assert "$0.00 USD" in status_reply
    assert "0건" in status_reply

    # 1-1. /status command with confirmed real settled trades
    live_ctx = dict(bot_ctx)
    live_ctx["dry_run"] = False
    live_ctx["has_real_closed_trades"] = True
    live_ctx["real_closed_pnl"] = 1250.75
    live_ctx["real_closed_trades"] = 18
    live_status_reply = telegram_bot.handle_command("/status", live_ctx)
    assert "+$1,250.75 USD" in live_status_reply
    assert "18건" in live_status_reply

    # 2. /balance command
    bal_reply = telegram_bot.handle_command("/balance", bot_ctx)
    assert "브로커 계좌 및 포트폴리오 자산 현황" in bal_reply
    assert "$4,550.00 USD" in bal_reply  # Free cash
    assert "$600.00 USD" in bal_reply    # Safe vault

    # 3. /positions command
    pos_reply = telegram_bot.handle_command("/positions", bot_ctx)
    assert "Cu" in pos_reply
    assert "$15,000.00" in pos_reply
    assert "$950.00" in pos_reply

    # 4. /pause & /resume commands
    pause_reply = telegram_bot.handle_command("/pause", bot_ctx)
    assert "봇 매매 일시 정지" in pause_reply

    resume_reply = telegram_bot.handle_command("/resume", bot_ctx)
    assert "봇 매매 정상 재개" in resume_reply

    # 5. /help command
    help_reply = telegram_bot.handle_command("/help", bot_ctx)
    assert "/status" in help_reply
    assert "/balance" in help_reply
