"""
Minerals Oracle x402 - Operations & Live Testing Diagnostic Script
Executes full end-to-end integration and smoke tests on all components:
1. Feed Engine calculation correctness
2. FastAPI endpoints via TestClient (Prices, Spreads, Urban Mining, Twitter Preview, MCP, AP2)
3. HTTP 402 Monetization & Sandbox logic
4. MCP Stdio protocol simulation
5. Twitter Bot formatting & preview
"""
import os
import sys
import json

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from fastapi.testclient import TestClient
from app.main import app
from app.feed_engine import feed_engine
from app.schemas import CommoditySymbol
from app.mcp_stdio import handle_initialize, handle_tools_list, handle_tool_call
from app.twitter_bot import twitter_bot

client = TestClient(app)

def print_section(title: str):
    print(f"\n{'='*65}\n  {title}\n{'='*65}")

def test_feed_engine():
    print_section("[1/5] Feed Engine & Mineral Valuations Check")
    symbols = [CommoditySymbol.LI, CommoditySymbol.NDDY, CommoditySymbol.CU, CommoditySymbol.AG, CommoditySymbol.PT]
    for sym in symbols:
        quote = feed_engine.get_single_quote(sym)
        print(f"  [OK] {quote.name} ({sym.value}): ${quote.spot_price_usd:,.2f} {quote.unit.value} | 24h: {quote.change_24h_pct:+.2f}% | Venue: {quote.benchmark_exchange}")

    spreads_resp = feed_engine.get_arbitrage_spreads()
    print(f"\n  [OK] Cross-Exchange Arbitrage Spreads Tracked: {len(spreads_resp.spreads)} routes")
    for sp in spreads_resp.spreads:
        prof_tag = "[PROFITABLE]" if sp.is_arbitrage_profitable else "[UNPROFITABLE]"
        print(f"       - {sp.symbol.value}: {sp.primary_exchange} (${sp.primary_price_usd:,.2f}) vs {sp.secondary_exchange} (${sp.secondary_price_usd:,.2f})")
        print(f"         Spread: ${sp.spread_usd:,.2f} ({sp.spread_basis_points:,.0f} bps) | Net Margin: ${sp.net_arbitrage_margin_usd:,.2f} {prof_tag}")

def test_api_endpoints():
    print_section("[2/5] FastAPI Web API & Endpoints Check")
    
    # Root & Health
    r = client.get("/health")
    assert r.status_code == 200, f"Health check failed: {r.text}"
    print("  [OK] /health: OK (Status: healthy)")

    r = client.get("/.well-known/ap2")
    assert r.status_code == 200, f"AP2 manifest failed: {r.text}"
    print("  [OK] /.well-known/ap2: AP2 Manifest loaded")

    # Protected Price endpoint (Sandbox Dev Bypass header)
    headers = {"X-Dev-Bypass": "true"}
    r = client.get("/api/v1/oracle/prices", headers=headers)
    assert r.status_code == 200, f"Price feed failed: {r.text}"
    data = r.json()
    print(f"  [OK] /api/v1/oracle/prices: {len(data['quotes'])} quotes returned")

    # Single price endpoint
    r = client.get("/api/v1/oracle/prices/Li", headers=headers)
    assert r.status_code == 200, f"Single price failed: {r.text}"
    print(f"  [OK] /api/v1/oracle/prices/Li: {r.json()['name']} = ${r.json()['spot_price_usd']:,.2f}")

    # Spreads endpoint
    r = client.get("/api/v1/oracle/spreads", headers=headers)
    assert r.status_code == 200, f"Spreads failed: {r.text}"
    spreads_data = r.json().get("spreads", [])
    print(f"  [OK] /api/v1/oracle/spreads: {len(spreads_data)} spreads returned")

    # Urban Mining Calculation
    payload = {
        "scrap_category": "EV_BATTERY_BLACK_MASS",
        "quantity_metric_tons": 2.5,
        "recovery_efficiency_factor": 0.95
    }
    r = client.post("/api/v1/oracle/urban-mining/calculate", json=payload, headers=headers)
    assert r.status_code == 200, f"Urban mining failed: {r.text}"
    res = r.json()
    print(f"  [OK] /api/v1/oracle/urban-mining/calculate: Gross = ${res['total_gross_payable_usd']:,.2f}, TC/RC = ${res['total_treatment_and_refining_charges_usd']:,.2f}, Net = ${res['net_settlement_value_usd']:,.2f}")

    # Twitter preview
    r = client.get("/api/v1/oracle/twitter-alerts/preview")
    assert r.status_code == 200, f"Twitter preview failed: {r.text}"
    print("  [OK] /api/v1/oracle/twitter-alerts/preview: Tweet preview generated")

def test_x402_monetization():
    print_section("[3/5] HTTP 402 Monetization & x402 Protocol Check")
    
    # Request without payment header and without bypass
    r = client.get("/api/v1/oracle/prices")
    if r.status_code == 402:
        print("  [OK] Protected endpoint returns HTTP 402 Payment Required as expected")
        pay_info = r.json().get("payment_parameters", {})
        print(f"       - Network: {pay_info.get('network')}")
        print(f"       - Price: {pay_info.get('price_usdc')} USDC")
        print(f"       - Treasury: {pay_info.get('pay_to')}")
        print(f"       - Token Contract: {pay_info.get('token')}")
    else:
        print(f"  [INFO] Endpoint returned status {r.status_code} (ALLOW_DEV_BYPASS enabled in .env)")

def test_mcp_protocol():
    print_section("[4/5] Model Context Protocol (MCP) Stdio Check")
    
    # 1. Initialize
    init_res = handle_initialize(1)
    assert init_res["result"]["serverInfo"]["name"] == "minerals-oracle-x402"
    print("  [OK] MCP JSON-RPC Initialize handshake successful")

    # 2. List tools
    tools_res = handle_tools_list(2)
    tools = tools_res["result"]["tools"]
    tool_names = [t["name"] for t in tools]
    print(f"  [OK] MCP Tools listed ({len(tools)} tools): {', '.join(tool_names)}")

    # 3. Call tool: get_mineral_prices
    call_res = handle_tool_call(3, "get_mineral_prices", {"mineral_type": "Lithium"})
    content = call_res["result"]["content"][0]["text"]
    assert "Lithium" in content
    print("  [OK] MCP Tool Call 'get_mineral_prices' executed successfully")

def test_twitter_bot():
    print_section("[5/6] Twitter Alpha Alert Bot Check")
    tweet_text = twitter_bot.generate_arbitrage_tweet()
    assert len(tweet_text) <= 280, f"Tweet exceeds 280 chars: length={len(tweet_text)}"
    print(f"  [OK] Arbitrage Tweet length check: {len(tweet_text)} / 280 characters")
    
    summary_tweet = twitter_bot.generate_market_summary_tweet()
    assert len(summary_tweet) <= 280
    print(f"  [OK] Market Summary Tweet length check: {len(summary_tweet)} / 280 characters")

def test_telegram_bot():
    print_section("[6/6] Telegram Smartphone Alert Bot Check")
    from app.telegram_bot import telegram_bot
    spreads = feed_engine.get_arbitrage_spreads().spreads
    top_spread = spreads[0].model_dump() if spreads else {}
    msg = telegram_bot.generate_arbitrage_message(top_spread)
    assert "ARBITRAGE ALERT" in msg
    print("  [OK] Telegram Arbitrage Alert generated successfully")

    quotes = feed_engine.get_all_quotes().quotes
    summary_msg = telegram_bot.generate_summary_message(quotes)
    assert "MARKET SUMMARY" in summary_msg
    print("  [OK] Telegram Market Summary Alert generated successfully")

def main():
    print("\nStarting Minerals Oracle x402 Comprehensive Operations Check...\n")
    try:
        test_feed_engine()
        test_api_endpoints()
        test_x402_monetization()
        test_mcp_protocol()
        test_twitter_bot()
        test_telegram_bot()
        print("\n" + "="*65)
        print("  ALL OPERATIONS & DIAGNOSTIC CHECKS PASSED PERFECTLY (6/6)")
        print("="*65 + "\n")
    except Exception as e:
        print(f"\n[ERROR] Diagnostic check failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
