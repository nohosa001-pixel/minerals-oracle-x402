# `@minerals-oracle/sdk`

Official TypeScript/Node.js SDK for **Minerals Oracle x402** — Autonomous AI Agent Critical Minerals Provenance, ESG Due Diligence, and Multi-Chain Trade Escrow Protocol.

[![npm version](https://img.shields.io/badge/npm-v1.0.0-blue.svg)](https://github.com/nohosa001-pixel/minerals-oracle-x402)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Production Status](https://img.shields.io/badge/Production-24%2F7_Cloud_Run_Seoul-brightgreen)](https://minerals-oracle-x402-7qxtp3324q-du.a.run.app/health)

---

## ⚡ 3-Line Quickstart

```typescript
import { MineralsOracleClient } from '@minerals-oracle/sdk';

const client = new MineralsOracleClient();
const res = await client.verifyTungsten({
  batch_id: 'W-APT-2026-T01',
  tenement_id: 'SANGDONG',
  latitude: 37.150,
  longitude: 128.833
});

console.log(res.audit_verdict?.status); // 'FULLY_COMPLIANT'
console.log(res.proof_hash);           // '0x...'
```

---

## 🤖 LangChain / Vercel AI SDK Integration

```typescript
import { createMineralsOracleTools } from '@minerals-oracle/sdk';

// Bind directly to any LangChain agent or LLM tools array
const tools = createMineralsOracleTools();
```

---

## 🛡️ Supported Verification Pipelines

- **`verifyLithium(input)`**: Australian Spodumene to LiOH, WA MINEDEX GIS Geofencing, stoichiometric mass balance (7.5:1).
- **`verifyNickel(input)`**: Indonesian HPAL MHP, ESDM SIMBARA tax, captive coal CBAM audit.
- **`verifyCobalt(input)`**: DRC Katanga Cobalt Hydroxide, CEEC seal, ILO 138/182 zero child labor audit.
- **`verifyCopper(input)`**: Chilean/Peruvian Copper Cathodes, ASTM B115 Grade 1, HVDC cables, COCHILCO quotas.
- **`verifySilver(input)`**: Mexican Silver Doré, N-Type TOPCon Solar PV paste purity (>=99.99%), LBMA good delivery.
- **`verifyTungsten(input)`**: Western Tungsten APT (Sangdong / Bakuta), US NDAA Sec 848 defense procurement.
- **`verifyRareEarths(input)`**: Allied NdPr (Sarfartoq / Silmet), China MOFCOM Notice 61 0.1% extraterritorial export defense.
- **`verifyNiobiumScandium(input)`**: NioCorp Elk Creek Ferroniobium (ASTM A550) & Scandium Oxide (Sc2O3 >= 99.5%), US DOE/EXIM loan.
- **`verifyCompositeBattery(payload)`**: NCM 811 Composite Master Passport with multi-stream Merkle root & EIP-712 signature.

---

## ⛓️ A2A Multi-Chain Escrow (Polygon · Base · Arbitrum · Solana)

```typescript
// Build deposit calldata for on-chain smart contract settlement
const calldata = await client.getEscrowCalldata('DEAL-2026-COP-003', 'solana');
console.log(calldata.escrow_contract_address); // 'DynSxW8JCy6296toTYrdhJqnoxtMvf3CPmtSSFEyqNnz'
console.log(calldata.calldata);                // 0x1df04324...
```

---

## 📄 License
MIT © nohosa001-pixel
