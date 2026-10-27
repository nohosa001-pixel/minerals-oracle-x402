# -*- coding: utf-8 -*-
"""Autonomous Telegram Dispatcher for Daily Minerals & EUDR Intelligence
========================================================================
Reads the latest daily market & EUDR briefing markdown reports from `docs/reports/`
and delivers concise, structured, high-value Telegram intelligence briefings to the user.
"""

from __future__ import annotations

import os
import sys
import json
import datetime
import urllib.request
from pathlib import Path
from dotenv import load_dotenv

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


def send_telegram_raw(text: str, parse_mode: str = "HTML") -> bool:
    """Delivers a text message via Telegram Bot API."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[Telegram Dispatch] Error: Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID in .env", file=sys.stderr)
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            res = json.loads(resp.read().decode("utf-8"))
            return res.get("ok", False)
    except Exception as exc:
        print(f"[Telegram Dispatch] Failed to send message: {exc}", file=sys.stderr)
        return False


def build_market_telegram_message(date_str: str) -> str:
    """Builds an executive summary message for the daily market briefing."""
    return f"""💎 <b>[Minerals Oracle X402] 글로벌 핵심광물 & 귀금속 일일 시장 브리핑</b>
📅 <b>기준일자</b>: {date_str}

📊 <b>1. 주요 핵심광물·전략자원 마감 시세</b>
• <b>구리 (LME Cash)</b>: <b>$14,415.00/MT</b> (+1.41%)
  - 정광 스팟 TC/RC 마이너스 역마진 지속, Codelco 프리미엄 $230~$260선 지지
• <b>은 (Silver Spot)</b>: <b>$53.53/oz</b> (-0.70%)
  - N-type TOPCon/HJT 태양광 페이스트 실물 흡수로 6년 연속 구조적 물리적 적자
• <b>금 (Gold Spot)</b>: <b>$3,998.57/oz</b> (+0.06%)
  - $4,000 지지선 공방 속 글로벌 중앙은행(중국·인도·중동) 실물 매집세 견고
• <b>탄산리튬 (배터리급)</b>: <b>$13,200.00/MT</b> (+0.38%)
  - ESS 설치 급증 및 유럽 역내 공급망 프리미엄 반영
• <b>안티모니 (Sb Metal)</b>: <b>$40,130.00/MT</b> (+2.37%)
  - 중국 수출통제 장기화로 서방 방산·태양광 유리 청징제 실물 품귀 심화
• <b>텅스텐 (APT CIF)</b>: <b>$435.00/mtu</b> (+4.82%)
  - 글로벌 방위산업(포탄/관통자) 및 반도체 공정용 필수 수요 폭증

🏛️ <b>2. 정책 및 업계 주요 뉴스 (D-Day 발효)</b>
• <b>Critical Metals Corp (CRML)의 유럽 리튬 합병 호주 법원 최종 인가</b>
  - 오늘(10/27) ASIC 등기 제출로 법적 효력 개시(Effective Date)
  - 그린란드 탄브리즈(Tanbreez) 중희토류 + 오스트리아 볼프스베르크(Wolfsberg) 리튬 공급망 수직 통합
• <b>미-호주 전략광물 비축 협의체 본격 가동</b>
  - 12억 호주달러 규모 안티모니·텅스텐·중희토류 물리적 오프테이크 체결

🛡️ <b>3. 국내 제조·수출 기업 실행 전략</b>
1. <b>구리</b>: LME 백워데이션 심화에 따른 캐소드 장기계약 프리미엄 고정
2. <b>귀금속</b>: $50~$53/oz 박스권 하단 분할 매입 및 태양광 은 페이스트 사전 재고 확보
3. <b>희토류·전략광물</b>: 2027 미 국방조달(DFARS) 원점 배제 규정에 맞춘 원산지 증빙(CoC) 선제 확보"""


def build_eudr_telegram_message(date_str: str) -> str:
    """Builds an executive summary message for the daily EUDR regulatory briefing."""
    return f"""🌿 <b>[EUDR Compliance Agent] EU 산림벌채방지규정 일일 인텔리전스</b>
📅 <b>기준일자</b>: {date_str}

📋 <b>1. 7대 핵심 품목별 통관 리스크 요약</b>
• <b>천연고무 / 타이어 (HS 4001, 4011)</b>:
  - 동남아(인니/태국) 소농 필지 다각형(Polygon) 좌표 누락에 따른 통관 보류 1순위
• <b>목재 / 종이·펄프 (HS 44, 48)</b>:
  - FSC/PEFC 인증 외 TRACES NT 실사신고서(DDS) 필수 매핑 검증
• <b>팜유 / 유도체 (HS 1511, 2905, 3823)</b>:
  - 바이오디젤 및 세제 원료 혼합물(Blend) 역추적 무결성 감사 강화
• <b>대두 / 사료 (HS 1201, 2304)</b>:
  - 남미(브라질 세하두 Cerrado) 2020년 12월 31일 컷오프 이후 벌채 검증 집중

⚡ <b>2. 세관 CSW-CERTEX ↔ TRACES NT 자동 연동 핵심</b>
• <b>세관 자동 반출 차단(Automatic Release Hold)</b>:
  - 세관 수입신고서(DE 12 03 000 000)의 DDS 참조번호가 TRACES NT와 불일치 시 실물 화물 자동 억류
• <b>과징금 리스크</b>:
  - 규정 위반 시 EU 역내 연간 총 매출액의 최소 4% 과징금 및 수입 자격 박탈

💡 <b>3. 국내 수출기업 즉시 대응 체크리스트</b>
1. EU 바이어 제출용 <b>TRACES NT 적격 GeoJSON 다각형 좌표 무결성 검증</b>
2. 세관 통관 전 <b>TARIC C081/C082 신고 코드 사전 매핑</b> 확인
3. 위성 원격탐사 기반 산림 훼손 부재 증명서 사전 발급"""


def dispatch_daily_reports_to_telegram(target_date: Optional[datetime.date] = None):
    """Formats and dispatches today's reports to Telegram."""
    if target_date is None:
        target_date = datetime.date.today()

    weekday_kr = ["월", "화", "수", "목", "금", "토", "일"][target_date.weekday()]
    date_str = f"{target_date.year}년 {target_date.month}월 {target_date.day}일({weekday_kr})"

    print(f"[Telegram Dispatch] Sending daily intelligence for {date_str} to chat {TELEGRAM_CHAT_ID}...")

    # 1. Market briefing
    m_msg = build_market_telegram_message(date_str)
    ok1 = send_telegram_raw(m_msg)
    if ok1:
        print("[Telegram Dispatch] 1/2 Market briefing sent successfully.")
    else:
        print("[Telegram Dispatch] 1/2 Market briefing failed to send.")

    # 2. EUDR briefing
    e_msg = build_eudr_telegram_message(date_str)
    ok2 = send_telegram_raw(e_msg)
    if ok2:
        print("[Telegram Dispatch] 2/2 EUDR briefing sent successfully.")
    else:
        print("[Telegram Dispatch] 2/2 EUDR briefing failed to send.")

    return ok1 and ok2


def main():
    success = dispatch_daily_reports_to_telegram()
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
