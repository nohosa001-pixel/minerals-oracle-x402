---
name: minerals-oracle
description: Real-time certified spot prices, cross-exchange arbitrage spreads, and metallurgical scrap yields for 5 critical raw minerals (Silver, Platinum, Copper, Lithium, Neodymium/Dysprosium). Monetized via HTTP 402 with Polygon/Base/Arbitrum USDC and native MCP tool compatibility.
---

# Minerals Oracle x402 - Agent Skill Guide

This skill equips autonomous AI agents (Claude Desktop, Cursor, CrewAI, AutoGPT, Antigravity) with tools and protocols to consume, query, and pay for physical commodities benchmarks and locational arbitrage spreads.

## Quick Reference & Capabilities

| Capability | Endpoint / MCP Tool | Pricing Tier | Tokens Saved |
| :--- | :--- | :--- | :--- |
| **All Spot Quotes** | `GET /api/v1/oracle/prices` | Standard ($0.005 USDC) | Use `?format=compact` (90% reduction) |
| **Single Mineral** | `GET /api/v1/oracle/prices/{symbol}` | Light ($0.001 USDC) | Use `?format=compact` (85% reduction) |
| **Arbitrage Spreads** | `GET /api/v1/oracle/spreads` | Standard ($0.005 USDC) | Use `?format=compact` (88% reduction) |
| **Scrap Yields** | `POST /api/v1/oracle/urban-mining/calculate` | Heavy ($0.010 USDC) | Rich JSON Breakdown |
| **Real-Time Stream** | `GET /api/v1/oracle/stream` | Free Event-Stream | Zero-Polling Push |
| **Instant Onboarding** | `POST /api/v1/agent/onboard` | Free (10 Free Queries) | 1-Click Provisioning |

---

## 1. Autonomous Self-Serve Onboarding

Before querying protected endpoints, any agent can self-register without human intervention:

```http
POST /api/v1/agent/onboard
Content-Type: application/json

{
  "agent_name": "AutonomousQuant-01",
  "requested_network": "polygon"
}
```

**Response**:

```json
{
  "status": "success",
  "session_key": "agent_session_a1b2c3d4...",
  "trial_balance_usdc": 0.05,
  "free_queries_remaining": 10,
  "auth_header": {
    "header_name": "X-Agent-Vault-Key",
    "header_value": "agent_session_a1b2c3d4..."
  }
}
```

---

## 2. Token-Saving Compact Format (Crucial for LLMs)

To prevent wasting context window tokens, always append `?format=compact` or send `Accept: text/plain`:

### A. All Spot Quotes

```bash
curl -H "X-Agent-Vault-Key: agent_session_..." "http://127.0.0.1:8000/api/v1/oracle/prices?format=compact"
```

**Output (~25 tokens vs 350 tokens)**:

```text
[CRM-QUOTE] Ag:65.9|Pt:1767.4|Cu:14559.3|Li:12850.0|NdDy:85.5
```

### B. Live Locational Arbitrage Spreads

```bash
curl -H "X-Agent-Vault-Key: agent_session_..." "http://127.0.0.1:8000/api/v1/oracle/spreads?format=compact"
```

**Output (~35 tokens vs 400 tokens)**:

```text
[CRM-SPREADS] Cu:COMEX-LME(+156bps,+$116.94) | Ag:COMEX-LBMA(+95bps,+$0.47) | Li:Fastmarkets-SMM(+638bps,+$399.19) | Pt:NYMEX-LPPM(+36bps,+$3.61)
```

---

## 3. Zero-Polling Server-Sent Events (SSE) Stream

Subscribe once to receive live push alerts only when profitable arbitrage opportunities occur:

```bash
curl -N "http://127.0.0.1:8000/api/v1/oracle/stream?min_bps=50.0"
```

**Stream Output**:

```text
event: connected
data: {"message": "Connected to Minerals Oracle x402 Live Stream", "filter_min_bps": 50.0}

event: arbitrage_alert
data: {"count": 2, "spreads": [{"symbol": "Cu", "spread_basis_points": 156.0, "net_arbitrage_margin_usd": 116.94}]}

event: heartbeat
data: {"timestamp_utc": "2026-09-03T08:10:00Z", "quotes": {"Ag": 65.88, "Cu": 14559.33, "Li": 12850.0}}
```

---

## 4. MCP Tools Integration (Claude Desktop / Cursor)

Add to `claude_desktop_config.json` or Cursor MCP configuration:

```json
{
  "mcpServers": {
    "minerals-oracle": {
      "command": "python",
      "args": ["-m", "app.mcp_stdio"]
    }
  }
}
```

Exposed Tools:

- `get_mineral_prices`: Fetches live spot quotes for specific or all critical minerals.
- `get_arbitrage_spreads`: Returns active COMEX, LME, LBMA, and SMM locational spreads.
- `calculate_urban_mining_value`: Calculates net recoverable value for scrap feedstock.
