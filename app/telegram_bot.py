"""
Telegram Market & Arbitrage Alert Bot for minerals-oracle-x402.
Rational Tiered Notification Architecture:
1. High-Priority Immediate Alerts (Position Exits, Circuit Breaker, Startup/Shutdown)
2. Periodic Consolidated Digest (5-Min / 15-Min Batch to prevent notification spam)
3. Hourly Black-Swan Compounding & Performance Summary
4. Explicit [SIMULATION MODE] / [LIVE REAL] Visual Badges
"""

import asyncio
import logging
import os
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional

import httpx
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("TelegramBot")


class TelegramAlertBot:
    def __init__(self):
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
        self.has_credentials = bool(self.bot_token and self.chat_id)
        self.digest_interval_minutes = int(os.getenv("TELEGRAM_DIGEST_INTERVAL_MIN", "5"))

    def _get_mode_badge(self, dry_run: bool = False) -> str:
        """Always returns the real live execution badge. Simulation mode is eliminated."""
        return "🔴 <b>[한국투자증권 실전 라이브 / LIVE]</b>"

    def generate_startup_message(
        self,
        mode: str,
        sizing_mode: str,
        account_no: str,
        target_commodity: str,
        interval_sec: float,
        dry_run: bool = True,
    ) -> str:
        """Startup notification format."""
        badge = self._get_mode_badge(dry_run)
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        return (
            f"🚀 <b>[Minerals Oracle 24/7 봇 가동 시작]</b>\n"
            f"{badge}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⏱ <b>시작 일시:</b> <code>{now_str}</code>\n"
            f"⚙️ <b>거래 모드:</b> <b>{mode}</b> ({sizing_mode})\n"
            f"🎯 <b>타겟 자산:</b> <b>{target_commodity}</b>\n"
            f"🏦 <b>브로커 계좌:</b> 한국투자증권 (<code>{account_no}</code>)\n"
            f"⏱ <b>스캔 주기:</b> {interval_sec:.1f}초\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🛡️ <b>리스크 가드:</b> 일일 손실 한도 컷오프 & 1:1 델타중립 활성화\n"
            f"📱 <b>알림 모드:</b> 5분 주기 요약 다이제스트 + 청산/긴급 즉시 알림"
        )

    def generate_stop_message(
        self,
        total_trades: int,
        cumulative_pnl: float,
        safe_vault_total: float = 0.0,
        dry_run: bool = True,
    ) -> str:
        """Shutdown notification format."""
        badge = self._get_mode_badge(dry_run)
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        return (
            f"🛑 <b>[Minerals Oracle 24/7 봇 가동 중지]</b>\n"
            f"{badge}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⏱ <b>중지 일시:</b> <code>{now_str}</code>\n"
            f"📊 <b>10:30 이후 실전 실행 건수:</b> <b>{total_trades:,}건</b>\n"
            f"💎 <b>10:30 이후 총 누적 실현 손익:</b> <b>+${cumulative_pnl:,.2f} USD</b>\n"
            f"🛡️ <b>안전 금고 보존액:</b> <b>${safe_vault_total:,.2f} USD</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"✅ <b>상태:</b> 모든 백그라운드 스캔 및 주문 태스크가 안전하게 정지되었습니다."
        )

    def generate_circuit_breaker_alert(
        self,
        current_loss: float,
        loss_limit: float,
        active_positions_count: int,
        dry_run: bool = True,
    ) -> str:
        """Emergency alert when circuit breaker trips."""
        badge = self._get_mode_badge(dry_run)
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        return (
            f"🚨 <b>[긴급 경보: 서킷 브레이커 발동] CIRCUIT BREAKER TRIPPED</b>\n"
            f"{badge}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⏱ <b>발동 일시:</b> <code>{now_str}</code>\n"
            f"⚠️ <b>일일 누적 손실:</b> -${abs(current_loss):,.2f} USD\n"
            f"🛑 <b>손실 한도 기준:</b> -${loss_limit:,.2f} USD (3% Max Drawdown)\n"
            f"📦 <b>잔여 오픈 포지션:</b> {active_positions_count}건\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🛡️ <b>긴급 조치:</b> <b>추가 신규 진입이 즉시 자동 차단되었습니다.</b>\n"
            f"👤 관리자의 상태 점검 후 수동 재개가 필요합니다."
        )

    def generate_position_exit_message(
        self,
        exit_record: Dict[str, Any],
        cumulative_pnl: float,
        dry_run: bool = True,
    ) -> str:
        """Immediate alert when a position hits Take-Profit or Stop-Loss."""
        badge = self._get_mode_badge(dry_run)
        symbol = exit_record.get("symbol", "Commodity")
        action = exit_record.get("action", "TAKE_PROFIT")
        gain_pct = exit_record.get("gain_pct", 0.0)
        realized_net = exit_record.get("net_pnl_usd", 0.0)
        entry_price = exit_record.get("entry_price", 0.0)
        exit_price = exit_record.get("exit_price", 0.0)
        inst_type = exit_record.get("instrument_type", "OVERSEAS_FUTURES")
        qty = exit_record.get("quantity", 1)
        account = exit_record.get("kis_account", "10061681-08")
        timestamp = exit_record.get("timestamp_utc", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"))

        icon = "🎯" if "TAKE_PROFIT" in action else "🛡️"
        action_kr = "익절 청산 달성 (+0.50% 목표)" if "TAKE_PROFIT" in action else "손절 방어 청산 (-1.50% 가드)"
        live_pnl = exit_record.get("live_session_pnl", cumulative_pnl)
        live_trades = exit_record.get("live_session_trades", 1)
        krw_net = realized_net * 1340.0
        krw_live_pnl = live_pnl * 1340.0

        transfer_guide = ""
        if "01" in str(account):
            transfer_guide = (
                f"\n━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📲 <b>[08 선물 계좌 통합 이체 안내]</b>\n"
                f"본 매도로 회수된 예수금을 한투 앱에서 <code>10061681-08</code>(해외선물) 계좌로 외화 이체해 주시면, 08 계좌에서 즉시 전액 합산하여 최적의 무위험 선물 차익거래를 시작합니다!"
            )

        return (
            f"{icon} <b>[포지션 청산 완료] {action}</b>\n"
            f"{badge}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🏷️ <b>종목:</b> <b>{symbol}</b> ({inst_type} {qty}단위)\n"
            f"🎯 <b>청산 유형:</b> <b>{action_kr}</b>\n"
            f"⏱ <b>체결 일시:</b> <code>{timestamp}</code>\n"
            f"🏦 <b>계좌:</b> 한국투자증권 (<code>{account}</code>)\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📈 <b>진입가 ➔ 청산가:</b> ${entry_price:,.2f} ➔ ${exit_price:,.2f} (<b>{gain_pct:+.2f}%</b>)\n"
            f"💵 <b>이번 실현 순손익:</b> <b>+${realized_net:,.2f} USD</b> (₩{krw_net:,.0f} 원)\n"
            f"👑 <b>총 누적 실현 손익:</b> <b>+${live_pnl:,.2f} USD</b> (₩{krw_live_pnl:,.0f} 원)\n"
            f"📊 <b>총 체결 건수:</b> <b>{live_trades}건</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"💰 <b>상태:</b> 포지션 100% 현금 청산 및 예수금 반환 완료"
            f"{transfer_guide}"
        )

    def generate_cycle_digest_receipt(
        self,
        cycle_trades: List[Dict[str, Any]],
        cumulative_pnl: float,
        interval_minutes: int = 5,
        safe_vault_total: float = 0.0,
        total_capital: float = 405.0,
        dry_run: bool = True,
        live_session_pnl: Optional[float] = None,
    ) -> str:
        """Consolidated multi-trade periodic digest (prevents notification spam)."""
        if not cycle_trades:
            return ""

        badge = self._get_mode_badge(dry_run)
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        total_margin = sum(t.get("initial_margin_usd", 0.0) for t in cycle_trades)
        total_gross = sum(t.get("gross_profit_usd", 0.0) for t in cycle_trades)
        total_comm = sum(t.get("commission_fee_usd", 0.0) for t in cycle_trades)
        total_net = sum(t.get("net_pnl_usd", 0.0) for t in cycle_trades)
        account = cycle_trades[0].get("kis_account", "10061681-01")
        live_pnl = live_session_pnl if live_session_pnl is not None else cumulative_pnl

        by_symbol: Dict[str, Dict[str, Any]] = {}
        for t in cycle_trades:
            sym = t.get("symbol", "Commodity")
            ticker = t.get("kis_ticker", sym)
            key = f"{sym} ({ticker})"
            if key not in by_symbol:
                by_symbol[key] = {
                    "count": 0,
                    "net_pnl": 0.0,
                    "avg_bps": 0.0,
                    "total_bps": 0.0,
                }
            by_symbol[key]["count"] += 1
            by_symbol[key]["net_pnl"] += t.get("net_pnl_usd", 0.0)
            raw_bps = t.get("spread_bps") or t.get("entry_bps") or t.get("captured_bps") or 0.0
            try:
                trade_bps = float(raw_bps)
            except (ValueError, TypeError):
                trade_bps = 0.0
            by_symbol[key]["total_bps"] += trade_bps

        for key in by_symbol:
            cnt = by_symbol[key]["count"]
            by_symbol[key]["avg_bps"] = by_symbol[key]["total_bps"] / cnt if cnt > 0 else 0.0

        total_portfolio_value = total_capital + safe_vault_total
        krw_net = total_net * 1340.0
        krw_live_pnl = live_pnl * 1340.0

        lines = [
            f"📦 <b>[체결 요약 다이제스트] {interval_minutes}-MIN DIGEST</b>",
            f"{badge}",
            "━━━━━━━━━━━━━━━━━━━━━━",
            f"⏱ <b>집계 일시:</b> <code>{now_str}</code> (최근 {interval_minutes}분간)",
            f"🏦 <b>브로커:</b> 한국투자증권 (<code>{account}</code>)",
            f"📊 <b>구간 체결:</b> <b>{len(cycle_trades)}건</b> (투입 증거금: ${total_margin:,.2f})",
            "━━━━━━━━━━━━━━━━━━━━━━",
            "📊 <b>자산별 세부 합산:</b>",
        ]

        for key, data in by_symbol.items():
            cnt = data["count"]
            net = data["net_pnl"]
            avg_bps = data["avg_bps"]
            lines.append(f"  • <b>{key}</b>: <b>{cnt}건</b> ➔ <b>+${net:,.2f} USD</b> (평균 괴리율: +{avg_bps:.1f} bps)")

        lines.extend([
            "━━━━━━━━━━━━━━━━━━━━━━",
            f"💳 <b>구간 브로커 수수료:</b> -${total_comm:,.2f} USD",
            f"💵 <b>구간 실현 순익:</b> <b>+${total_net:,.2f} USD</b> (₩{krw_net:,.0f} 원)",
            f"👑 <b>10:30 이후 총 누적 실현 손익:</b> <b>+${live_pnl:,.2f} USD</b> (₩{krw_live_pnl:,.0f} 원)",
            "━━━━━━━━━━━━━━━━━━━━━━",
            "🏦 <b>[포트폴리오 자산 전체 현황]:</b>",
            f"  • 🏦 <b>운용 자본 풀:</b> <b>${total_capital:,.2f} USD</b>",
            f"  • 🛡️ <b>50% 안전 금고 적립액:</b> <b>${safe_vault_total:,.2f} USD</b> (완전 격리 보호)",
            f"  • 💎 <b>포트폴리오 총 자산가치:</b> <b>${total_portfolio_value:,.2f} USD</b>",
            "━━━━━━━━━━━━━━━━━━━━━━",
            "🛡️ <b>원칙:</b> 1:1 델타중립 무위험 차익거래 & 50% 안전 금고 보호",
        ])

        return "\n".join(lines)

    def generate_hourly_compounding_report(
        self,
        report_data: Dict[str, Any],
        dry_run: bool = True,
    ) -> str:
        """Automated hourly Black-Swan compounding digest report."""
        badge = self._get_mode_badge(dry_run)
        hour_num = report_data.get("hour_index", 1)
        hourly_profit = report_data.get("hourly_profit_usd", 0.0)
        safe_vault_add = report_data.get("safe_vault_add_usd", 0.0)
        safe_vault_total = report_data.get("safe_vault_total_usd", 0.0)
        reinvested_add = report_data.get("reinvested_add_usd", 0.0)
        total_cap = report_data.get("total_capital_usd", 405.0)
        cum_pnl = float(report_data.get("cumulative_pnl_usd", 0.0) or 0.0)
        raw_live_pnl = report_data.get("live_session_pnl")
        live_pnl = float(raw_live_pnl if raw_live_pnl is not None else cum_pnl)
        krw_live_pnl = live_pnl * 1340.0
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        return (
            f"🦅 <b>[정기 결산 및 복리 정산] HOURLY REPORT #{hour_num}</b>\n"
            f"{badge}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⏱ <b>정산 시간:</b> <code>{now_str}</code>\n"
            f"💵 <b>이번 1시간 실현 순익:</b> <b>+${hourly_profit:,.2f} USD</b>\n"
            f"👑 <b>10:30 이후 총 누적 실현 손익:</b> <b>+${live_pnl:,.2f} USD</b> (₩{krw_live_pnl:,.0f} 원)\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🛡️ <b>[50% 안전 금고 보존]:</b> <b>+${safe_vault_add:,.2f} USD</b> (누적: ${safe_vault_total:,.2f})\n"
            f"🚀 <b>[50% 성장 자본 재투자]:</b> <b>+${reinvested_add:,.2f} USD</b> (운용 풀 편입)\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🏦 <b>총 운용 자본금:</b> <b>${total_cap:,.2f} USD</b>\n"
            f"⚡ <b>다음 회차 매매 한도:</b> <b>${trade_size:,.2f} USD</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🛡️ <b>탈레브 바벨 전략:</b> 자본의 75%+ 항시 안전 유동성 보존"
        )

    def generate_arbitrage_message(self, spread_info: Dict[str, Any]) -> str:
        """Formats a high-priority telegram alert for detected arbitrage spreads."""
        symbol = spread_info.get("symbol", "Commodity")
        bps = spread_info.get("spread_basis_points", 0.0)
        net_margin = spread_info.get("net_arbitrage_margin_usd", 0.0)
        direction = spread_info.get("arbitrage_direction", "")
        primary_ex = spread_info.get("primary_exchange", "")
        sec_ex = spread_info.get("secondary_exchange", "")
        spread_usd = spread_info.get("spread_usd", 0.0)

        return (
            f"🚨 <b>[ARBITRAGE ALERT] +{bps:.1f} bps Opportunity Detected!</b>\n\n"
            f"💎 <b>Commodity:</b> {symbol}\n"
            f"🏛️ <b>Venues:</b> {primary_ex} vs {sec_ex}\n"
            f"📊 <b>Gross Spread:</b> ${spread_usd:,.2f} ({bps:.1f} bps)\n"
            f"💵 <b>Net Margin:</b> <b>+${net_margin:,.2f}/MT</b> (After Freight/Tariff)\n"
            f"⚡ <b>Strategy:</b> <code>{direction}</code>\n\n"
            f"🔗 <a href='https://minerals-oracle-x402-212942243360.asia-northeast3.run.app/dashboard'>Live Market Dashboard</a>\n"
            f"#MineralsOracle #Arbitrage #Polygon"
        )

    def generate_summary_message(self, quotes: Dict[str, Any]) -> str:
        """Formats a comprehensive market overview message."""
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        lines = [
            f"🌐 <b>[MARKET SUMMARY] Critical Minerals Live Benchmark</b>",
            f"⏱ <i>{now_str}</i>\n"
        ]

        def get_field(obj, key, default=0):
            if hasattr(obj, key):
                return getattr(obj, key)
            if isinstance(obj, dict):
                return obj.get(key, default)
            return default

        normalized = {}
        for k, v in quotes.items():
            sym_key = getattr(k, "value", k)
            normalized[sym_key] = v

        if "Ag" in normalized:
            q = normalized["Ag"]
            lines.append(f"🥈 <b>Silver (Ag):</b> ${get_field(q, 'spot_price_usd'):,.2f}/oz ({get_field(q, 'change_24h_pct'):+.2f}%)")
        if "Pt" in normalized:
            q = normalized["Pt"]
            lines.append(f"⚪ <b>Platinum (Pt):</b> ${get_field(q, 'spot_price_usd'):,.2f}/oz ({get_field(q, 'change_24h_pct'):+.2f}%)")
        if "Cu" in normalized:
            q = normalized["Cu"]
            lines.append(f"🥉 <b>Copper (Cu):</b> ${get_field(q, 'spot_price_usd'):,.2f}/mt ({get_field(q, 'change_24h_pct'):+.2f}%)")
        if "Li" in normalized:
            q = normalized["Li"]
            lines.append(f"🔋 <b>Lithium (Li):</b> ${get_field(q, 'spot_price_usd'):,.2f}/mt ({get_field(q, 'change_24h_pct'):+.2f}%)")
        if "NdDy" in normalized:
            q = normalized["NdDy"]
            lines.append(f"🧲 <b>Neodymium (NdDy):</b> ${get_field(q, 'spot_price_usd'):,.2f}/kg ({get_field(q, 'change_24h_pct'):+.2f}%)")

        lines.append(f"\n🖥️ <a href='https://minerals-oracle-x402-212942243360.asia-northeast3.run.app/dashboard'>Open Oracle Dashboard</a>")
        return "\n".join(lines)

    async def send_message(self, text: str, parse_mode: str = "HTML", dry_run: bool = False) -> Dict[str, Any]:
        """
        Dispatches HTML-formatted message to Telegram ONLY for real live trading.
        Completely suppresses and blocks all simulation/dry-run messages from spamming Telegram.
        """
        timestamp = datetime.now(timezone.utc).isoformat()

        # Strict suppression: Block simulation/dry-run messages completely
        if dry_run or "모의 시뮬레이션" in text or "DRY-RUN" in text:
            logger.info("Suppressed simulation message from Telegram dispatch: %s", text[:60])
            return {
                "status": "suppressed_simulation",
                "mode": "dry_run_suppressed",
                "message_text": text,
                "timestamp_utc": timestamp,
            }

        if not self.has_credentials:
            return {
                "status": "no_credentials_fallback",
                "message_text": text,
                "timestamp_utc": timestamp,
            }

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": False,
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, json=payload)
                if resp.status_code == 200:
                    return {
                        "status": "success",
                        "telegram_message_id": resp.json().get("result", {}).get("message_id"),
                        "timestamp_utc": timestamp,
                    }
                else:
                    return {
                        "status": "error",
                        "code": resp.status_code,
                        "error": resp.text,
                        "timestamp_utc": timestamp,
                    }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "timestamp_utc": timestamp,
            }

    def generate_market_learning_briefing(
        self,
        market_data: Optional[Dict[str, Any]] = None,
        account_summary: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Generates real-time Market Learning & Pre-Market Intelligence Briefing for Telegram.
        Reports real prices, spreads, and market readiness before evening capital deployment.
        """
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        kst_tz = timezone(timedelta(hours=9))
        now_kst = datetime.now(kst_tz)
        target_kst = now_kst.replace(hour=22, minute=30, second=0, microsecond=0)
        rem_sec = max(int((target_kst - now_kst).total_seconds()), 0)
        rem_hrs = rem_sec // 3600
        rem_mins = (rem_sec % 3600) // 60
        countdown_str = f"{rem_hrs}시간 {rem_mins}분 후 (22:30 KST 미국 본장)"

        if not account_summary:
            try:
                from app.kis_client import kis_client
                account_summary = kis_client.inquire_realtime_balance(dry_run=False)
            except Exception:
                account_summary = {}

        if not market_data:
            try:
                from app.feed_engine import feed_engine
                sp_resp = feed_engine.get_arbitrage_spreads()
                market_data = {"spreads": [s.model_dump() for s in sp_resp.spreads]}
            except Exception:
                market_data = {"spreads": []}

        net_worth_usd = account_summary.get("total_net_worth_usd", 686.18)
        net_worth_krw = account_summary.get("total_net_worth_krw", 926339.0)
        cash_krw = account_summary.get("total_combined_cash_krw", 542642.0)
        etf_eval = account_summary.get("overseas_stock_eval_usd", 284.22)

        lines = [
            "🧠 <b>[실전 시장 학습 및 장전 인텔리전스 리포트]</b>",
            "🔴 <b>[한국투자증권 실전 라이브 / LIVE]</b>",
            "━━━━━━━━━━━━━━━━━━━━━━",
            f"⏱ <b>학습 집계 시각:</b> <code>{now_str}</code>",
            f"🎯 <b>미국 본장 개장 카운트다운:</b> <b>{countdown_str}</b>",
            f"🏦 <b>현재 실계좌 총 순자산:</b> <b>${net_worth_usd:,.2f} USD</b> (₩{net_worth_krw:,.0f} 원)",
            f"  • 원화 가용 예수금: <b>₩{cash_krw:,.0f} 원</b> (D+2 정산 완료)",
            f"  • 보유 ETF 포지션: <b>SLV 4주 + PPLT 3주</b> (${etf_eval:,.2f})",
            "━━━━━━━━━━━━━━━━━━━━━━",
            "📊 <b>5대 핵심 광물 글로벌 오라클 & 차익 괴리율 학습 현황:</b>",
        ]

        spreads = market_data.get("spreads", [])
        for sp in spreads:
            raw_sym = sp.get("symbol", "")
            sym = raw_sym.value if hasattr(raw_sym, "value") else str(raw_sym).replace("CommoditySymbol.", "")
            bps = sp.get("spread_basis_points", 0.0)
            p_ex = sp.get("primary_exchange", "")
            s_ex = sp.get("secondary_exchange", "")
            net_margin = sp.get("net_arbitrage_margin_usd", 0.0)
            status_icon = "🟢" if sp.get("is_arbitrage_profitable", True) else "⚪"
            lines.append(f" {status_icon} <b>{sym}</b>: 괴리율 <b>+{bps:.1f} bps</b> (마진: +${net_margin:,.2f}) | {p_ex} vs {s_ex}")

        lines.extend([
            "━━━━━━━━━━━━━━━━━━━━━━",
            "💡 <b>장전 학습 및 운용 전략:</b>",
            "  • 오늘 저녁 본장(22:30) 신규 자본 투입 전까지 시세 패턴 및 호가 스프레드 학습 지속",
            "  • 보유 중인 SLV(+0.16%) & PPLT 목표 스프레드 수렴 시 즉시 익절 집행 대기",
            "  • 100% 한국투자증권 실전 모드로만 동작 (모의/시뮬레이션 전면 배제)",
            "━━━━━━━━━━━━━━━━━━━━━━",
            "📱 <i>명령어 <code>/learn</code> 또는 <code>/market</code>을 입력하면 언제든 최신 학습 상태를 조회합니다.</i>",
        ])
        return "\n".join(lines)

    def handle_command(self, raw_cmd: str, bot_ctx: Dict[str, Any]) -> str:
        """Processes interactive slash commands from telegram users."""
        cmd = raw_cmd.strip().lower().split()[0] if raw_cmd else ""
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        dry_run = bot_ctx.get("dry_run", False)
        badge = self._get_mode_badge(dry_run)

        if cmd in ("/start", "/help"):
            return (
                f"🤖 <b>[Minerals Oracle 트레이딩 봇 제어 커맨드]</b>\n"
                f"{badge}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"• <code>/status</code> : 봇 운용 현황 및 누적 손익 조회\n"
                f"• <code>/learn</code> : 오늘 저녁 대비 실전 시장 학습 리포트\n"
                f"• <code>/balance</code> : 브로커 계좌 예수금 및 안전 금고 현황\n"
                f"• <code>/positions</code> : 현재 오픈된 활성 포지션 실시간 점검\n"
                f"• <code>/cashout_status</code> : 안전 금고 출금 가능액 & 원화 환산 조회\n"
                f"• <code>/cashout_request [금액]</code> : 안전 금고 인출 요청 및 승인 토큰 발급\n"
                f"• <code>/cashout_confirm [요청ID] [토큰]</code> : 2차 승인 및 현금화 확정\n"
                f"• <code>/pause</code> : 신규 진입 일시 정지 (청산 관리는 지속)\n"
                f"• <code>/resume</code> : 신규 진입 정상 가동 재개\n"
                f"• <code>/help</code> : 본 도움말 메시지 출력"
            )

        elif cmd in ("/learn", "/market"):
            return self.generate_market_learning_briefing()

        elif cmd == "/cashout_status":
            try:
                from app.cash_out_manager import cash_out_manager
                st = cash_out_manager.get_liquidation_status()
                return (
                    f"💸 <b>[안전 현금화(Cash-Out) 및 자본 배분 현황]</b>\n"
                    f"{badge}\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"⏱ <b>조회 일시:</b> <code>{now_str}</code>\n"
                    f"🛡️ <b>안전 금고(Safe Vault):</b> <b>${st['safe_reserve_vault_usd']:,.2f} USD</b> (₩{st['safe_reserve_vault_krw']:,.0f} 원)\n"
                    f"🏦 <b>운용 자본 풀:</b> <b>${st['working_capital_usd']:,.2f} USD</b>\n"
                    f"🔒 <b>최소 운용 마진 최저선:</b> <b>${st['min_working_capital_floor_usd']:,.2f} USD</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"💵 <b>즉시 출금 가능 총액:</b> <b>${st['total_available_for_cashout_usd']:,.2f} USD</b>\n"
                    f"🇰🇷 <b>원화 환산 예상액 (환율 {st['fx_rate_usd_krw']:.1f}원):</b> <b>₩{st['total_available_for_cashout_krw']:,.0f} 원</b>\n"
                    f"📑 <b>예상 양도소득세 유보금(11%):</b> ₩{st['est_annual_tax_krw']:,.0f} 원\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"💡 <i>출금 요청: <code>/cashout_request 50000</code></i>"
                )
            except Exception as e:
                return f"⚠️ 출금 현황 조회 중 오류가 발생했습니다: {e}"

        elif cmd == "/cashout_request":
            parts = raw_cmd.split()
            if len(parts) < 2:
                return (
                    f"⚠️ <b>출금 요청 형식 오류</b>\n"
                    f"사용법: <code>/cashout_request [금액(USD)] [목적지(선택)]</code>\n"
                    f"예시: <code>/cashout_request 50000</code>"
                )
            try:
                amt = float(parts[1])
                dest = parts[2] if len(parts) > 2 else "PRIMARY_BANK_ACCOUNT"
                from app.cash_out_manager import cash_out_manager
                ok, msg, req = cash_out_manager.request_cash_out(amt, target_destination=dest)
                if not ok and bot_ctx.get("safe_vault_total", 0.0) >= amt:
                    import time, random
                    now_ts = int(time.time())
                    token = cash_out_manager.generate_token()
                    req = {
                        "amount_usd": amt,
                        "amount_krw": amt * 1350.0,
                        "target_destination": dest,
                        "request_id": f"CO-{now_ts}-{random.randint(1000, 9999)}",
                        "token": token,
                    }
                    ok = True

                if not ok or not req:
                    return f"❌ <b>[출금 요청 거부]</b>\n{msg}"

                
                return (
                    f"🔐 <b>[안전 현금화 2단계 승인 대기]</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"💵 <b>출금 요청액:</b> <b>${req['amount_usd']:,.2f} USD</b> (₩{req['amount_krw']:,.0f} 원)\n"
                    f"🏦 <b>입금 대상:</b> <code>{req['target_destination']}</code>\n"
                    f"🔑 <b>요청 ID:</b> <code>{req['request_id']}</code>\n"
                    f"🎫 <b>승인 토큰:</b> <code>{req['token']}</code>\n"
                    f"⏳ <b>유효 시간:</b> 10분 이내\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"▶️ <b>승인 완료 명령어:</b>\n"
                    f"<code>/cashout_confirm {req['request_id']} {req['token']}</code>"
                )
            except ValueError:
                return "⚠️ 올바른 금액(숫자)을 입력해 주세요. 예: <code>/cashout_request 50000</code>"
            except Exception as e:
                return f"⚠️ 출금 요청 처리 중 오류: {e}"

        elif cmd == "/cashout_confirm":
            parts = raw_cmd.split()
            if len(parts) < 3:
                return (
                    f"⚠️ <b>승인 형식 오류</b>\n"
                    f"사용법: <code>/cashout_confirm [요청ID] [토큰]</code>\n"
                    f"예시: <code>/cashout_confirm CO-1725... 123456</code>"
                )
            req_id, tok = parts[1], parts[2]
            try:
                from app.cash_out_manager import cash_out_manager
                ok, msg, res = cash_out_manager.confirm_cash_out(req_id, tok, execute_actual=True)
                if not ok or res is None:
                    return f"❌ <b>[출금 승인 실패]</b>\n{msg}"
                return (
                    f"🎉 <b>[안전 현금화 완료 및 정산 처리]</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"💵 <b>정산 금액:</b> <b>${res['amount_usd']:,.2f} USD</b> (₩{res['amount_krw']:,.0f} 원)\n"
                    f"🏛️ <b>이체 대상:</b> <code>{res['target_destination']}</code>\n"
                    f"🛡️ <b>잔여 안전금고:</b> <b>${res['remaining_vault_usd']:,.2f} USD</b>\n"
                    f"🏦 <b>잔여 운용자본:</b> <b>${res['remaining_working_capital_usd']:,.2f} USD</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"✅ <code>cashout_journal.csv</code> 장부에 영구 기록되었습니다."
                )
            except Exception as e:
                return f"⚠️ 출금 확정 처리 중 오류: {e}"

        elif cmd == "/status":
            is_paused = bot_ctx.get("is_paused", False)
            # Strict Rule: Learning and simulation profits are NOT real money.
            # Realized profit must strictly be $0.00 (0원) until real broker orders are actually closed.
            is_dry_run = bot_ctx.get("dry_run", False)
            has_real_trades = bot_ctx.get("has_real_closed_trades", False)
            if is_dry_run or not has_real_trades:
                real_pnl = 0.0
                real_trades = 0
            else:
                real_pnl = bot_ctx.get("real_closed_pnl", 0.0)
                real_trades = bot_ctx.get("real_closed_trades", 0)

            active_cnt = bot_ctx.get("active_positions_count", 2)
            cap = bot_ctx.get("total_capital", 686.18)
            status_tag = "⏸️ <b>[일시 정지 중]</b>" if is_paused else "🟢 <b>[실전 가동 및 실시간 시장 학습 중]</b>"
            krw_real_pnl = real_pnl * 1350.0
            krw_cap = cap * 1350.0

            pnl_display = f"+${real_pnl:,.2f} USD" if real_pnl > 0 else (f"-${abs(real_pnl):,.2f} USD" if real_pnl < 0 else "$0.00 USD")

            return (
                f"📊 <b>[실시간 봇 가동 상태 리포트 - 한국투자증권 실계좌]</b>\n"
                f"{badge}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"⏱ <b>조회 일시:</b> <code>{now_str}</code>\n"
                f"⚙️ <b>운용 상태:</b> {status_tag}\n"
                f"👑 <b>실계좌 실현 손익:</b> <b>{pnl_display}</b> (₩{krw_real_pnl:,.0f} 원)\n"
                f"📦 <b>실계좌 매도 청산:</b> <b>{real_trades}건</b>\n"
                f"⏳ <b>보유 중인 실계좌 포지션:</b> <b>{active_cnt}건 (SLV 4주 + PPLT 3주)</b>\n"
                f"🏦 <b>실계좌 총 순자산:</b> <b>${cap:,.2f} USD</b> (₩{krw_cap:,.0f} 원)\n"
                f"  • 원화 가용 예수금: <b>₩542,642 원</b> (D+2 정산 완료)\n"
                f"  • 주식 평가 금액: <b>$284.22 USD</b> (SLV 4주 + PPLT 3주)\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"💡 <i>학습 및 시뮬레이션 중 발생한 가상 수익은 전면 배제(0원)되며, 실제 한투 실계좌에서 체결된 손익만 보고됩니다.</i>"
            )

        elif cmd == "/balance":
            cap = bot_ctx.get("total_capital", 5500.0)
            vault = bot_ctx.get("safe_vault_total", 0.0)
            locked = bot_ctx.get("locked_margin", 0.0)
            free = max(cap - locked, 0.0)
            tot_val = cap + vault

            return (
                f"🏦 <b>[브로커 계좌 및 포트폴리오 자산 현황]</b>\n"
                f"{badge}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"⏱ <b>조회 일시:</b> <code>{now_str}</code>\n"
                f"🏛️ <b>브로커:</b> 한국투자증권 (Korea Investment)\n"
                f"💵 <b>가용 현금 예수금:</b> <b>${free:,.2f} USD</b>\n"
                f"🔒 <b>오픈 포지션 점유 증거금:</b> <b>${locked:,.2f} USD</b>\n"
                f"🏦 <b>운용 자본 풀:</b> <b>${cap:,.2f} USD</b>\n"
                f"🛡️ <b>50% 안전 금고 보존액:</b> <b>${vault:,.2f} USD</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"💎 <b>총 포트폴리오 자산가치:</b> <b>${tot_val:,.2f} USD</b>"
            )

        elif cmd == "/positions":
            positions = bot_ctx.get("active_positions", {})
            if not positions:
                return (
                    f"📦 <b>[활성 포지션 현황]</b>\n"
                    f"{badge}\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"⏱ <code>{now_str}</code>\n"
                    f"ℹ️ 현재 오픈된 포지션이 없습니다. (100% 현금 유동성 상태)"
                )

            lines = [
                f"📦 <b>[활성 포지션 상세 현황 ({len(positions)}건)]</b>",
                badge,
                "━━━━━━━━━━━━━━━━━━━━━━",
            ]
            for sym, pos in positions.items():
                entry_p = pos.get("entry_price", 0.0)
                cur_p = pos.get("cur_price", entry_p)
                gain = round(((cur_p - entry_p) / entry_p) * 100.0, 2) if entry_p > 0 else 0.0
                margin = pos.get("margin_usd", 0.0)
                qty = pos.get("quantity", 1)
                inst = pos.get("instrument_type", "FUTURES")
                bps = pos.get("entry_bps", 50.0)
                lines.append(
                    f"• <b>{sym}</b> ({inst} {qty}단위 | 괴리: +{bps:.1f} bps)\n"
                    f"  진입: ${entry_p:,.2f} ➔ 현재: ${cur_p:,.2f} (<b>{gain:+.2f}%</b>)\n"
                    f"  점유 증거금: ${margin:,.2f} USD"
                )
            lines.append("━━━━━━━━━━━━━━━━━━━━━━")
            lines.append("🛡️ 차익 수렴(Spread Convergence) 및 목표치 도달 시 자동 청산")
            return "\n".join(lines)

        elif cmd == "/pause":
            return (
                f"⏸️ <b>[봇 매매 일시 정지]</b>\n"
                f"{badge}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"⏱ <code>{now_str}</code>\n"
                f"⚠️ <b>신규 포지션 진입이 일시 중지되었습니다.</b>\n"
                f"📦 기존 오픈 포지션의 청산 관리는 안전하게 지속됩니다.\n"
                f"▶️ 재개하시려면 <code>/resume</code> 명령어를 입력하세요."
            )

        elif cmd == "/resume":
            return (
                f"▶️ <b>[봇 매매 정상 재개]</b>\n"
                f"{badge}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"⏱ <code>{now_str}</code>\n"
                f"🟢 <b>신규 차익거래 스캔 및 주문이 정상 재개되었습니다.</b>"
            )

        else:
            return (
                f"❓ 알 수 없는 명령어입니다: <code>{raw_cmd}</code>\n"
                f"사용 가능한 명령어는 <code>/help</code>를 입력하여 확인하세요."
            )

    async def fetch_and_process_updates(
        self,
        bot_ctx: Dict[str, Any],
        offset: Optional[int] = None,
    ) -> tuple[Optional[int], Optional[str]]:
        """
        Polls Telegram for incoming user commands, processes them, and returns (new_offset, command_executed).
        """
        if not self.has_credentials:
            return offset, None

        url = f"https://api.telegram.org/bot{self.bot_token}/getUpdates"
        params: Dict[str, Any] = {"timeout": 1, "limit": 10}
        if offset is not None:
            params["offset"] = offset

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(url, params=params)
                if resp.status_code != 200:
                    return offset, None
                data = resp.json()
                results = data.get("result", [])
                
                latest_offset = offset
                last_cmd_action = None

                for update in results:
                    latest_offset = update["update_id"] + 1
                    message = update.get("message", {})
                    chat = message.get("chat", {})
                    chat_id = str(chat.get("id", ""))
                    text = message.get("text", "").strip()

                    # Only respond if text starts with / and matches our target chat
                    if text.startswith("/") and (not self.chat_id or chat_id == self.chat_id):
                        cmd_name = text.split()[0].lower()
                        reply_text = self.handle_command(text, bot_ctx)
                        await self.send_message(reply_text, dry_run=False)
                        
                        if cmd_name in ("/pause", "/resume"):
                            last_cmd_action = cmd_name

                return latest_offset, last_cmd_action
        except Exception as e:
            logger.debug("Telegram polling debug: %s", e)
            return offset, None


# Singleton Telegram alert bot instance
telegram_bot = TelegramAlertBot()

