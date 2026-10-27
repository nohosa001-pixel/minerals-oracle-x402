# -*- coding: utf-8 -*-
"""Autonomous Daily Critical Minerals & Precious Metals Market Intelligence Generator
=====================================================================================
Uses Google Gemini 3.8 Flash with Google Search Grounding to automatically research,
synthesize, and generate comprehensive daily market briefing reports, archiving them
in `docs/reports/` and feeding extracted signals into Minerals Oracle & A.GRID systems.
"""

from __future__ import annotations

import os
import sys
import argparse
import datetime
from pathlib import Path
from dotenv import load_dotenv

# Reconfigure console output for UTF-8
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Project root directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

try:
    from google import genai
    from google.genai import types
except ImportError:
    print("[ERROR] 'google-genai' package is required. Install via pip install google-genai", file=sys.stderr)
    sys.exit(1)


SYSTEM_INSTRUCTION = """당신은 'Minerals Oracle X402 Intelligence Desk'의 수석 글로벌 원자재 및 핵심광물 분석가입니다.
실시간 Google Search 검색 결과를 기반으로, 최신 글로벌 거래소(LME, COMEX, SHFE, LBMA), 외신(Mining.com, Bloomberg, Reuters, Streetwise Reports, InvestorNews 등), 각국 정부 공시(EU 집행위, 미 국방부/에너지부, 중국 상무부)의 팩트와 최신 시세를 정밀하게 취합하여 최고 수준의 종합 분석 보고서를 한국어로 작성합니다.
반드시 모든 섹션을 명확한 수치, 링크 출처(마크다운 하이퍼링크), 구체적인 계약 프리미엄, D-Day 타임라인을 포함하여 작성해야 합니다."""


PROMPT_TEMPLATE = """오늘은 {target_date_str}입니다.
오늘({target_date_str}) 기준 최신 글로벌 핵심광물 및 귀금속 시장 동향 보고서를 아래 6개 섹션 구조에 맞추어 전문적이고 심층적으로 작성해주세요.
주말인 경우 주간 마감 확정치와 주말 장외/현물 동향을 종합하여 반영합니다.

[반드시 포함해야 할 6개 섹션]:
# 글로벌 핵심광물 및 귀금속 시장 종합 동향 보고서 ({target_date_iso})

- **보고 일시**: {target_date_str} 기준
- **분석 주관**: Minerals Oracle X402 Intelligence Desk

---

## 1. 주요 핵심광물 및 귀금속 주간/일간 마감 시세 총괄표 (10대 핵심광물 + 전략광물)
(구리, 은, 금, 리튬, 니켈, 코발트, 알루미늄, 희토류 NdPr, 흑연, 망간, 텅스텐, 안티모니)
- 마크다운 테이블 형식: | 광물/원자재명 | 거래 단위 | 최근 확정 시세 (USD) | 주간/일간 변동률 | 글로벌 재고 및 수급 밸런스 | 핵심 가격 결정 변수 |
- 각 원자재별로 실시간 검색된 최신 출처 링크(Westmetall, Trading Economics, Mining.com 등)를 포함할 것.

---

## 2. 3대 전략 금속 심층 분석: 구리, 은, 금
- (1) 구리 (Copper): LME/COMEX 시세, Codelco 등 주요 제련사 캐소드 프리미엄(TC/RC), 미국/유럽/아시아 재고 디커플링
- (2) 은 (Silver): 주말/선물 시세, 국제 유가/거시 긴축 영향, 골드/실버 비율(GSR), 태양광(N-type TOPCon/HJT) 실물 페이스트 수요
- (3) 금 (Gold): $4,000선 공방 및 심리적 지지선, 지정학적 위기(호르무즈 해협 등) 속 마진콜 청산 및 중앙은행 매입 구조적 복원력

---

## 3. 글로벌 자원 공급망 정책 및 업계 긴급 뉴스
- 핵심광물 기업 M&A, 주요 법원 심리(Critical Metals Corp 등), 고품위 광구 인수 계약
- 주요국 정상회의 및 전략광물 조달 협약(캐나다-EU, 미-호주 등) 최신 진척 상황

---

## 4. 탄소국경조정제도(CBAM) 및 공급망 실사(CSDDD) 규제 심층 분석
- (1) EU CBAM 확정기 공인 검증 데이터 의무화 및 국가별 기본값 할증(Mark-up: 2026년 +10%, 2027년 +20%) 페널티 체계
- (2) EU CSDDD(공급망 실사 지침) 및 IAA(산업가속법 역내 조달율 70%) 연계 파급 효과

---

## 5. 주요국 광물 법제화 현황 및 산업 현장 파급 효과
- (1) 중국: 상무부 제61호 공고 중희토류 0.1% 역외 통제 재발효 타임라인 및 통관 리스크
- (2) 미국: 국방수탁조달규정(DFARS) 2027 완전 배제 시행령 카운트다운 및 디지털 광물 여권 의무화

---

## 6. 국내 제조 및 수출 기업을 위한 핵심 실행 전략
- 구리 캐소드 장기 공급 계약 고정 전략
- 귀금속 단기 변동성 활용 원료 분할 매입 가이드
- 희토류 및 핵심광물 원산지 증빙(CoC) 사전 확보 방안
"""


def get_gemini_client() -> genai.Client:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is missing from environment. Please check .env file.")
    return genai.Client(api_key=api_key)


def generate_market_briefing(target_date: Optional[datetime.date] = None) -> tuple[Path, str]:
    """Generates the briefing using Gemini 3.8 Flash with Google Search Grounding and saves it to docs/reports."""
    if target_date is None:
        target_date = datetime.date.today()

    target_date_iso = target_date.strftime("%Y-%m-%d")
    weekday_kr = ["월", "화", "수", "목", "금", "토", "일"][target_date.weekday()]
    target_date_str = f"{target_date.year}년 {target_date.month}월 {target_date.day}일({weekday_kr})"

    print(f"[Minerals Oracle Intelligence] Generating market report for {target_date_str}...")

    client = get_gemini_client()
    model_name = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")

    prompt = PROMPT_TEMPLATE.format(
        target_date_str=target_date_str,
        target_date_iso=target_date_iso,
    )

    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_INSTRUCTION,
        tools=[types.Tool(google_search=types.GoogleSearch())],
        temperature=0.2,
    )

    print(f"[Minerals Oracle Intelligence] Querying {model_name} with Google Search Grounding...")
    response = client.models.generate_content(
        model=model_name,
        contents=prompt,
        config=config,
    )

    content = response.text or ""
    if not content.strip():
        raise RuntimeError("Received empty response from Gemini API.")

    # Target file path
    reports_dir = PROJECT_ROOT / "docs" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_file = reports_dir / f"{target_date_iso}_market_briefing.md"

    # Write report
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"[Minerals Oracle Intelligence] Successfully saved report to {report_file} ({len(content)} chars)")
    return report_file, content


def main():
    parser = argparse.ArgumentParser(description="Autonomous Daily Market Briefing Generator")
    parser.add_argument("--date", type=str, help="Target date in YYYY-MM-DD format (default: today)")
    parser.add_argument("--dry-run", action="store_true", help="Print report to console without overwriting file")
    args = parser.parse_args()

    target_date = None
    if args.date:
        try:
            target_date = datetime.datetime.strptime(args.date, "%Y-%m-%d").date()
        except ValueError:
            print(f"[ERROR] Invalid date format: {args.date}. Use YYYY-MM-DD.", file=sys.stderr)
            sys.exit(1)

    try:
        report_file, content = generate_market_briefing(target_date)
        if args.dry_run:
            print("\n" + "=" * 80)
            print(content[:500] + "\n...\n[TRUNCATED]")
            print("=" * 80)
    except Exception as exc:
        print(f"[ERROR] Failed to generate market briefing: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
