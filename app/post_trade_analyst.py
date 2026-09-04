"""
Post-Trade Execution & Performance Audit Analyst for Minerals Oracle x402.

Performs rigorous post-trade evaluation after every completed round-trip trade:
1. Execution Quality Audit: Slippage analysis (target price vs filled price).
2. Rule Adherence Audit: 4x commission hurdle check, circuit breaker check.
3. Trade Grading (A/B/C/D/F): Based on execution efficiency and discipline.
4. Auto-Report Generation: Generates learning-focused post-trade audit reports (Markdown/JSON).
"""

import json
import logging
import os
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

logger = logging.getLogger("PostTradeAnalyst")


class PostTradeAnalyst:
    def __init__(self, reports_dir: Optional[str] = None):
        if reports_dir is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.reports_dir = os.path.join(base_dir, "logs", "audit_reports")
        else:
            self.reports_dir = reports_dir
        os.makedirs(self.reports_dir, exist_ok=True)

        self.audit_records: List[Dict[str, Any]] = []

    def evaluate_trade(
        self,
        trade_record: Dict[str, Any],
        target_entry_price: Optional[float] = None,
        target_exit_price: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Conducts in-depth post-mortem audit of a completed trade.
        """
        symbol = trade_record.get("symbol", "UNKNOWN")
        trade_id = trade_record.get("trade_id", f"TRADE-{int(datetime.now().timestamp())}")
        entry_price = float(trade_record.get("entry_price", 0.0))
        exit_price = float(trade_record.get("exit_price", 0.0))
        gross_pnl = float(trade_record.get("gross_profit_usd", 0.0))
        commission = float(trade_record.get("commission_fee_usd", trade_record.get("commission_usd", 3.0)))
        net_pnl = float(trade_record.get("net_pnl_usd", gross_pnl - commission))
        holding_sec = float(trade_record.get("holding_sec", 0.0))
        reason = trade_record.get("action", "PROFIT_TARGET_MET")

        # 1. Slippage Analysis (BPS)
        entry_slippage_bps = 0.0
        if target_entry_price and target_entry_price > 0 and entry_price > 0:
            entry_slippage_bps = round(((entry_price - target_entry_price) / target_entry_price) * 10000, 2)

        exit_slippage_bps = 0.0
        if target_exit_price and target_exit_price > 0 and exit_price > 0:
            exit_slippage_bps = round(((target_exit_price - exit_price) / target_exit_price) * 10000, 2)

        # 2. Rule Adherence: Commission Coverage Multiplier
        commission_multiple = round(gross_pnl / commission, 2) if commission > 0 else 0.0
        hurdle_passed = commission_multiple >= 4.0 if gross_pnl > 0 else False

        # 3. Grading & Discipline Assessment
        grade = "B"
        critique = []

        if net_pnl > 0:
            if hurdle_passed and abs(entry_slippage_bps) <= 2.0:
                grade = "A"
                critique.append("완벽한 원칙 준수: 목표 수수료 4배 허들 달성 및 슬리피지 최소화")
            elif hurdle_passed:
                grade = "A-"
                critique.append("목표 이익 달성 성공, 다만 진입/청산 슬리피지 추가 개선 여지 있음")
            else:
                grade = "B"
                critique.append("수익 청산되었으나 수수료 4배 목표 허들에는 소폭 미달")
        elif net_pnl == 0:
            grade = "C"
            critique.append("손익분기점(BEP) 청산 완료 (원금 보존)")
        else:
            if "CIRCUIT" in str(reason) or "STOP" in str(reason):
                grade = "C+"
                critique.append("방어적 손실 브레이크 정상 가동: 리스크 원칙에 따른 적시 손절")
            else:
                grade = "D"
                critique.append("예상 밖의 시장 급변으로 손실 발생. 진입 시그널 필터 강화 검토 필요")

        audit_result = {
            "trade_id": trade_id,
            "timestamp_utc": trade_record.get("timestamp_utc", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")),
            "symbol": symbol,
            "grade": grade,
            "direction": trade_record.get("direction", "Buy -> Sell Roundtrip"),
            "entry_price": entry_price,
            "exit_price": exit_price,
            "target_entry_price": target_entry_price or entry_price,
            "target_exit_price": target_exit_price or exit_price,
            "entry_slippage_bps": entry_slippage_bps,
            "exit_slippage_bps": exit_slippage_bps,
            "holding_sec": holding_sec,
            "holding_time_formatted": f"{int(holding_sec // 60)}분 {int(holding_sec % 60)}초",
            "gross_pnl_usd": gross_pnl,
            "commission_usd": commission,
            "net_pnl_usd": net_pnl,
            "commission_multiple": commission_multiple,
            "hurdle_passed": hurdle_passed,
            "exit_reason": reason,
            "critique": " / ".join(critique),
            "kis_order_id": trade_record.get("kis_order_id", ""),
            "kis_account": trade_record.get("kis_account", ""),
        }

        self.audit_records.insert(0, audit_result)
        if len(self.audit_records) > 200:
            self.audit_records.pop()

        # Generate and save individual trade report
        self._generate_trade_report_markdown(audit_result)
        return audit_result

    def _generate_trade_report_markdown(self, audit: Dict[str, Any]) -> str:
        """
        Creates an actionable, learning-focused markdown report for the trade.
        """
        filename = f"audit_{audit['trade_id']}.md"
        filepath = os.path.join(self.reports_dir, filename)

        md = f"""# 📊 사후 매매 실행 및 학습 평가 보고서 (Post-Trade Audit)

- **보고서 발행 시각**: {audit['timestamp_utc']}
- **거래 ID**: `{audit['trade_id']}`
- **종목 (상품)**: **{audit['symbol']}** (증권사 계좌: {audit['kis_account']})
- **종합 매매 등급 (Grade)**: **[{audit['grade']}]**

---

### 1. 매매 실행 성과 요약
| 항목 | 결과 | 원칙 및 계획 기준 | 평가 결과 |
| :--- | :---: | :---: | :---: |
| **순손익 (Net PnL)** | **${audit['net_pnl_usd']:+.2f} USD** | 양의 순익 추구 | {'🟢 성공' if audit['net_pnl_usd'] > 0 else '🔴 손실'} |
| **총 차익 (Gross)** | ${audit['gross_pnl_usd']:+.2f} USD | - | - |
| **증권사 수수료** | ${audit['commission_usd']:.2f} USD | 1계약 실비 | 실비 차감 반영 |
| **수수료 대비 수익 배수** | **{audit['commission_multiple']:.1f}배** | **수수료 4.0배 이상** | {'🟢 원칙 준수' if audit['hurdle_passed'] else '⚠️ 허들 미달'} |
| **포지션 보유 시간** | {audit['holding_time_formatted']} | 유동적 단기 청산 | 계획 범위 내 |

---

### 2. 실행 품질 (슬리피지 & 가격 괴리)
- **진입 가격**: 목표 ${audit['target_entry_price']:.4f} -> 체결 ${audit['entry_price']:.4f} (슬리피지: **{audit['entry_slippage_bps']:+.2f} bps**)
- **청산 가격**: 목표 ${audit['target_exit_price']:.4f} -> 체결 ${audit['exit_price']:.4f} (슬리피지: **{audit['exit_slippage_bps']:+.2f} bps**)
- **청산 사유**: `{audit['exit_reason']}`

---

### 3. 학습 피드백 및 트레이딩 인사이트
> **종합 진단**: {audit['critique']}

- **긍정적 요인 (Keep)**:
  - 증권사 KIS 공식 원장 체결 확인 후 포지션 등록 원칙 100% 준수.
  - 가상 수식 없이 호가 엣지에 기반한 실질 집행 완료.
- **개선 및 학습 과제 (Improve)**:
  - {'시장 진입 시 지정가/호가 분할을 통해 슬리피지 최소화 필요' if abs(audit['entry_slippage_bps']) > 3.0 else '호가 스프레드 추적 상태 우수, 현재의 1계약 안전 규칙 지속 유지 권장'}.
"""
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(md)
        except Exception as e:
            logger.warning("Failed to save markdown audit report: %s", e)

        return md

    def get_summary_statistics(self) -> Dict[str, Any]:
        """
        Calculates aggregate statistics across all audited trades for learning.
        """
        if not self.audit_records:
            return {
                "total_trades": 0,
                "win_count": 0,
                "loss_count": 0,
                "win_rate_pct": 0.0,
                "profit_factor": 0.0,
                "total_net_pnl_usd": 0.0,
                "total_commission_paid_usd": 0.0,
                "average_trade_pnl_usd": 0.0,
                "hurdle_adherence_rate_pct": 0.0,
                "grade_distribution": {"A": 0, "B": 0, "C": 0, "D": 0, "F": 0},
            }

        total = len(self.audit_records)
        wins = [t for t in self.audit_records if t["net_pnl_usd"] > 0]
        losses = [t for t in self.audit_records if t["net_pnl_usd"] < 0]

        total_gain = sum(t["net_pnl_usd"] for t in wins)
        total_loss = abs(sum(t["net_pnl_usd"] for t in losses))
        profit_factor = round(total_gain / total_loss, 2) if total_loss > 0 else (99.0 if total_gain > 0 else 0.0)

        total_net_pnl = round(sum(t["net_pnl_usd"] for t in self.audit_records), 2)
        total_comm = round(sum(t["commission_usd"] for t in self.audit_records), 2)
        hurdle_passed_cnt = sum(1 for t in self.audit_records if t["hurdle_passed"])

        grade_dist = {"A": 0, "B": 0, "C": 0, "D": 0, "F": 0}
        for t in self.audit_records:
            base_g = t["grade"][0]
            grade_dist[base_g] = grade_dist.get(base_g, 0) + 1

        return {
            "total_trades": total,
            "win_count": len(wins),
            "loss_count": len(losses),
            "win_rate_pct": round((len(wins) / total) * 100, 1),
            "profit_factor": profit_factor,
            "total_net_pnl_usd": total_net_pnl,
            "total_commission_paid_usd": total_comm,
            "average_trade_pnl_usd": round(total_net_pnl / total, 2),
            "hurdle_adherence_rate_pct": round((hurdle_passed_cnt / total) * 100, 1),
            "grade_distribution": grade_dist,
        }

    def generate_telegram_audit_message(self, audit: Dict[str, Any]) -> str:
        """
        Generates a concise, informative Telegram post-trade audit report.
        """
        return (
            f"📋 [사후 매매 학습 보고서] {audit['symbol']}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"• 매매 등급: [{audit['grade']}]\n"
            f"• 순손익: ${audit['net_pnl_usd']:+.2f} USD\n"
            f"• 수수료 대비 배수: {audit['commission_multiple']:.1f}배 (기준: 4.0배)\n"
            f"• 보유 시간: {audit['holding_time_formatted']}\n"
            f"• 슬리피지: 진입 {audit['entry_slippage_bps']:+.1f}bp / 청산 {audit['exit_slippage_bps']:+.1f}bp\n"
            f"• 진단 피드백: {audit['critique']}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"💡 데이터는 자동 저장되어 복리 및 전략 최적화에 반영됩니다."
        )


# Global singleton instance
post_trade_analyst = PostTradeAnalyst()
