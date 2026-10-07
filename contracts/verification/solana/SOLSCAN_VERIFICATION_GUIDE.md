# Solana Mainnet Solscan Program Verification & Registration Guide

This guide provides complete instructions and pre-packaged files to register, verify, and tag **Minerals Oracle x402** programs on **Solscan** ([solscan.io](https://solscan.io)) and **Solana Explorer** ([explorer.solana.com](https://explorer.solana.com)).

---

## 1. Registered Program Directory

| Program Name | Program ID (Base58) | Solscan Explorer URL | Purpose |
| :--- | :--- | :--- | :--- |
| **DynamicTradeEscrow** | `DynSxW8JCy6296toTYrdhJqnoxtMvf3CPmtSSFEyqNnz` | [Solscan Link](https://solscan.io/account/DynSxW8JCy6296toTYrdhJqnoxtMvf3CPmtSSFEyqNnz#anchorProgramIdl) | Mark-to-Market Pyth Escrow with Tripartite Delivery & Autonomous Margin Call |
| **UniversalEscrowCore** | `AGR3W3R9pKxnuZGYrpaggfkbMKVrjoniLaGvi1voBFSC` | [Solscan Link](https://solscan.io/account/AGR3W3R9pKxnuZGYrpaggfkbMKVrjoniLaGvi1voBFSC) | 0.4s Direct Split Universal Escrow & Ed25519 Truth Attestation |
| **AgentPaymentVault** | `7oZ16YaazQzN6z5uA1nAZWD9oGUDXyvHwXGJLFYyWi3y` | [Solscan Link](https://solscan.io/account/7oZ16YaazQzN6z5uA1nAZWD9oGUDXyvHwXGJLFYyWi3y) | AI Autonomous Agent Pre-Funded Vault (<1ms Query Fast-Path) |
| **MineralsOracleConsumer** | `21ZR1QCyAbNrRLs1iWEkdbNsfCFdJcy6ip9R2JxDbkTL` | [Solscan Link](https://solscan.io/account/21ZR1QCyAbNrRLs1iWEkdbNsfCFdJcy6ip9R2JxDbkTL) | Verifiable Spot Price & Battery Passport Merkle Root Consumer |

- **Official Treasury Wallet**: `411ksMz9RHYVtVMe6RUUErzZYtrU9zzvkgzswKbqx9qp`
- **Settlement Token**: SPL USDC (`EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v`)
- **Network**: `Solana Mainnet-Beta` (Chain ID: `501`)

---

## 2. Step 1: Upload Anchor IDL on Solscan (Decoded Instructions)

Registering the Anchor IDL (Interface Definition Language) allows Solscan to decode raw instruction bytes into human-readable functions (`createDeal`, `anchorOracleProof`, `confirmCarrierArrival`, `checkMarginCall`, `settleDeal`) and account parameters.

### Method A: Web UI Upload (Quickest - No CLI Required)

1. Open Solscan for **DynamicTradeEscrow**:
   - [DynamicTradeEscrow on Solscan](https://solscan.io/account/DynSxW8JCy6296toTYrdhJqnoxtMvf3CPmtSSFEyqNnz#anchorProgramIdl)
2. Click on the **"Anchor"** or **"Program IDL"** tab on the account page.
3. Click **"Upload IDL"** / **"Verify IDL"**.
4. Select the matching pre-built IDL file:
   - 📁 [`contracts/verification/solana/dynamic_trade_escrow.idl.json`](dynamic_trade_escrow.idl.json)
5. Connect the Program Upgrade Authority wallet (`411ksMz9...`) to sign and confirm ownership.

### Method B: On-Chain IDL Upload / Upgrade via Anchor CLI

If you have Anchor CLI installed with the program deployer keypair:

```bash
# 1. DynamicTradeEscrow (Update / Initialize IDL on Escrow Program)
anchor idl init -f contracts/verification/solana/dynamic_trade_escrow.idl.json \
  DynSxW8JCy6296toTYrdhJqnoxtMvf3CPmtSSFEyqNnz \
  --provider.cluster https://api.mainnet-beta.solana.com

# 2. AgentPaymentVault
anchor idl init -f contracts/verification/solana/agent_payment_vault.idl.json \
  7oZ16YaazQzN6z5uA1nAZWD9oGUDXyvHwXGJLFYyWi3y \
  --provider.cluster https://api.mainnet-beta.solana.com

# 3. MineralsOracleConsumer
anchor idl init -f contracts/verification/solana/minerals_oracle_consumer.idl.json \
  21ZR1QCyAbNrRLs1iWEkdbNsfCFdJcy6ip9R2JxDbkTL \
  --provider.cluster https://api.mainnet-beta.solana.com
```


---

## 3. Step 2: Solscan Project Verification & Official Label Application

To get verified tags, official labels, and logo displays on Solscan (e.g., displaying "Minerals Oracle Universal Escrow" instead of an anonymous address), submit the **Solscan Account Verification Request**.

- **Solscan Support / Verification Portal**: [https://forms.solscan.io/](https://forms.solscan.io/) or [https://solscan.io/contact-us](https://solscan.io/contact-us)

### Pre-Filled Submission Details

```yaml
Project Name: Minerals Oracle x402
Project Tag: minerals-oracle
Category: Oracle / Autonomous AI Agent / Real World Assets (RWA)
Website: https://minerals-oracle-x402.com
GitHub: https://github.com/nohosa001-pixel/minerals-oracle-x402
Treasury Wallet: 411ksMz9RHYVtVMe6RUUErzZYtrU9zzvkgzswKbqx9qp
Settlement Currency: USDC (EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v)

Programs to Label:
  1. AGR3W3R9pKxnuZGYrpaggfkbMKVrjoniLaGvi1voBFSC:
     Label: "Minerals Oracle: Universal Escrow Core"
     Description: "Sub-second 0.4s direct split settlement with Ed25519 truth attestation"
  2. 7oZ16YaazQzN6z5uA1nAZWD9oGUDXyvHwXGJLFYyWi3y:
     Label: "Minerals Oracle: Agent Payment Vault"
     Description: "Autonomous AI agent pre-funded micro-payment vault under HTTP 402"
  3. 21ZR1QCyAbNrRLs1iWEkdbNsfCFdJcy6ip9R2JxDbkTL:
     Label: "Minerals Oracle: Oracle Consumer"
     Description: "On-chain critical mineral spot pricing and Battery Passport verifier"

Compliance & Audits:
  - EUDR 2023/1115 (European Union Deforestation Regulation)
  - US IRA Section 30D (Foreign Entity of Concern <25% Screening)
  - OECD Due Diligence Annex II (Mass Balance Stoichiometry)
  - EU AI Act Article 50 (Dual-Attestation Machine-to-Machine Trust)
```

---

## 4. Verification Checklist & Testing

Once uploaded, verify on Solscan:

1. Search `AGR3W3R9pKxnuZGYrpaggfkbMKVrjoniLaGvi1voBFSC` on [solscan.io](https://solscan.io).
2. Check that the program shows "Anchor Program: universal_escrow_core".
3. Check that the instructions list shows:
   - `initializeEscrow`
   - `executeDirectSplit`
   - `refundEscrow`
4. Confirm that transactions originating from `POST /api/v1/escrow/universal/settle-solana` show decoded transfers to `411ksMz9RHYVtVMe6RUUErzZYtrU9zzvkgzswKbqx9qp` (0.1% Treasury Fee).
