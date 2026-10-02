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
| **Security Gate Status** | `GET /api/v1/oracle/security-gate/status` | Free Telemetry | Zero-Trust Circuit Breaker & Domain Metrics |
| **Minerals Escrow Rail** | `POST /api/v1/escrow/universal/settle-minerals` | Escrow Direct Split | Atomic Payouts + EIP-712 Attestation (Domain 4) |
| **EUDR Escrow Rail** | `POST /api/v1/escrow/universal/settle-eudr` | Escrow Direct Split | Deforestation-Free Concession Payouts (Domain 3) |
| **Solana Truth Attest** | `POST /api/v1/escrow/universal/solana/attest` | Ed25519 Oracle Attest | 64-Byte Ed25519 Signature for Solana Programs |
| **Solana Direct Settle** | `POST /api/v1/escrow/universal/settle-solana` | 0.4s Fast Settlement | 99.8% Seller / 0.1% Treasury / 0.1% Staking Pool |
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

Exposed Tools (32 Agent Tools Available):

- `eudr_satellite_mine_audit`: Sentinel-1/2 SAR radar deforestation & indigenous land protection audit with TRACES-NT DDS.
- `verify_composite_battery_passport`: End-to-end composite EV battery pack compliance (US IRA 30D + EU 2023/1542).
- `verify_lithium_origin` / `verify_nickel_origin` / `verify_cobalt_origin` / `verify_copper_origin` / `verify_silver_origin`: Single mineral origin pipelines.
- `optimize_mineral_trade_route`: Autonomous landed cost arbitrage ($/MT) and chokepoint bypass decision signal.
- `propose_a2a_trade_deal` / `dual_sign_trade_deal`: Bilateral trade agreement negotiation and dual-signing.
- `get_compliance_status` / `calculate_trade_tariffs`: Real-time compliance status and bilateral trade tariff resolution.

---

## 5. Security Gate x402 Universal Escrow & Truth Attestation Rail

Minerals Oracle bridges directly with the deployed `agent-security-gate-x402` to provide cryptographic truth validation and atomic escrow settlement:

### A. Conflict-Free Minerals Truth Settlement (Domain 4: CONFLICT_MINERALS)

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/escrow/universal/settle-minerals" \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "job_minerals_lithium_001",
    "mineral_type": "lithium",
    "smelter_id": "CID001928",
    "smelter_audit_status": "CONFORMANT",
    "mine_country_code": "AU",
    "chain_of_custody_verified": true,
    "child_labor_free": true,
    "recipients": [{"recipient": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8", "amount": 75000.0}]
  }'
```

### B. Deforestation-Free Forest Concession Settlement (Domain 3: EUDR_FOREST)

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/escrow/universal/settle-eudr" \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "job_eudr_timber_001",
    "commodity": "timber",
    "country_code": "ID",
    "polygon_coordinates": [[-3.12, -60.02], [-3.12, -60.01], [-3.13, -60.01]],
    "dds_reference_id": "EU-DDS-2026-ID-01",
    "deforestation_detected": false,
    "legal_harvest_verified": true,
    "recipients": [{"recipient": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8", "amount": 50000.0}]
  }'
```

### C. Live Security Gate Health & Circuit Breaker Telemetry

```bash
curl "http://127.0.0.1:8000/api/v1/oracle/security-gate/status"
```

---

## 6. Solana Mainnet-Beta Sub-Second (0.4s) Direct Split & Ed25519 Oracle Rail

Connects directly with Solana Mainnet-Beta for high-frequency algorithmic commodity settlement:
- **Chain ID**: `501`
- **Native Token**: `SOL` | **Settlement Asset**: SPL USDC (`EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v`)
- **Finality Speed**: `0.4s (400ms)`
- **Treasury Address**: `411ksMz9RHYVtVMe6RUUErzZYtrU9zzvkgzswKbqx9qp`
- **RPC URL**: `https://api.mainnet-beta.solana.com`

### A. Request Ed25519 Oracle Truth Attestation for Solana

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/escrow/universal/solana/attest" \
  -H "Content-Type: application/json" \
  -d '{
    "domain": "CONFLICT_MINERALS",
    "domain_id": 4,
    "query_payload": {
      "smelter_id": "CID002991",
      "mineral": "cobalt",
      "provenance_status": "VERIFIED"
    },
    "client_identity": "411ksMz9RHYVtVMe6RUUErzZYtrU9zzvkgzswKbqx9qp",
    "confidence_score": 0.999
  }'
```

### B. Sub-Second Direct Split Universal Escrow Settlement on Solana

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/escrow/universal/settle-solana" \
  -H "Content-Type: application/json" \
  -d '{
    "deal_id": "DEAL-SOLANA-MINERAL-001",
    "buyer_agent_pubkey": "BuyerAgent111111111111111111111111111111111",
    "seller_agent_pubkey": "SellerAgent11111111111111111111111111111111",
    "gross_amount_usdc": 1000.0,
    "oracle_domain": "CONFLICT_MINERALS",
    "oracle_id": 4
  }'
```

**Direct Split Distribution**:
- **Seller Agent Net (99.8%)**: $998.00 USDC
- **Minerals Oracle Treasury (0.1%)**: $1.00 USDC to `411ksMz9RHYVtVMe6RUUErzZYtrU9zzvkgzswKbqx9qp`
- **Security Gate Staking Pool (0.1%)**: $1.00 USDC to `774hK5wmk5pStvsh5DH46pYPYYD3ro7tMfz1ASxcbiTK`

