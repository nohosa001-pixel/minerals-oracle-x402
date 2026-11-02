# Solana Mainnet Solscan Program Verification & Registration Guide

This guide provides complete instructions and pre-packaged files to register, verify, and tag **Minerals Oracle x402** programs on **Solscan** ([solscan.io](https://solscan.io)) and **Solana Explorer** ([explorer.solana.com](https://explorer.solana.com)).

---

## 1. Registered Program Directory

| Program Name | Program ID (Base58) | Solscan Explorer URL | Purpose |
| :--- | :--- | :--- | :--- |
| **TradeFinanceSettlementEngine** | `TrdFx402ZkR3M5vW9aK7nB1pQ2eC8sY6tU4jH7vL9mNp` | [Solscan Link](https://solscan.io/account/TrdFx402ZkR3M5vW9aK7nB1pQ2eC8sY6tU4jH7vL9mNp#anchorProgramIdl) | SGS/Intertek Umpire Arbitration, TRACES NT DDS Grounding & 15 bps Protocol Fee Capture |
| **DynamicTradeEscrow** | `DynSxW8JCy6296toTYrdhJqnoxtMvf3CPmtSSFEyqNnz` | [Solscan Link](https://solscan.io/account/DynSxW8JCy6296toTYrdhJqnoxtMvf3CPmtSSFEyqNnz#anchorProgramIdl) | Mark-to-Market Pyth Escrow with Tripartite Delivery & Autonomous Margin Call |
| **UniversalEscrowCore** | `AGR3W3R9pKxnuZGYrpaggfkbMKVrjoniLaGvi1voBFSC` | [Solscan Link](https://solscan.io/account/AGR3W3R9pKxnuZGYrpaggfkbMKVrjoniLaGvi1voBFSC) | 0.4s Direct Split Universal Escrow & Ed25519 Truth Attestation |
| **AgentPaymentVault** | `7oZ16YaazQzN6z5uA1nAZWD9oGUDXyvHwXGJLFYyWi3y` | [Solscan Link](https://solscan.io/account/7oZ16YaazQzN6z5uA1nAZWD9oGUDXyvHwXGJLFYyWi3y) | AI Autonomous Agent Pre-Funded Vault (<1ms Query Fast-Path) |
| **MineralsOracleConsumer** | `21ZR1QCyAbNrRLs1iWEkdbNsfCFdJcy6ip9R2JxDbkTL` | [Solscan Link](https://solscan.io/account/21ZR1QCyAbNrRLs1iWEkdbNsfCFdJcy6ip9R2JxDbkTL) | Verifiable Spot Price & Battery Passport Merkle Root Consumer |

- **Official Treasury Wallet**: `411ksMz9RHYVtVMe6RUUErzZYtrU9zzvkgzswKbqx9qp`
- **Settlement Token**: SPL USDC (`EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v`)
- **Network**: `Solana Mainnet-Beta` (Chain ID: `501`)

---

## 2. Step 1: Upload Anchor IDL on Solscan (Decoded Instructions)

Registering the Anchor IDL (Interface Definition Language) allows Solscan to decode raw instruction bytes into human-readable functions (`fundConsignmentDeal`, `verifyTracesDdsGrounding`, `executeCommercialSettlement`, `createDeal`, `anchorOracleProof`, `confirmCarrierArrival`, `checkMarginCall`, `settleDeal`) and account parameters.

### Method A: Web UI Upload (Quickest - No CLI Required)

1. Open Solscan for **TradeFinanceSettlementEngine**:
   - [TradeFinanceSettlementEngine on Solscan](https://solscan.io/account/TrdFx402ZkR3M5vW9aK7nB1pQ2eC8sY6tU4jH7vL9mNp#anchorProgramIdl)
2. Click on the **"Anchor"** or **"Program IDL"** tab on the account page.
3. Click **"Upload IDL"** / **"Verify IDL"**.
4. Select the matching pre-built IDL file:
   - 📁 [`contracts/verification/solana/trade_finance_settlement_engine.idl.json`](trade_finance_settlement_engine.idl.json)
5. Connect the Program Upgrade Authority wallet (`411ksMz9...`) to sign and confirm ownership.

### Method B: On-Chain IDL Upload / Upgrade via Anchor CLI

If you have Anchor CLI installed with the program deployer keypair:

```bash
# 1. TradeFinanceSettlementEngine (Initialize IDL on Solana Settlement Program)
anchor idl init -f contracts/verification/solana/trade_finance_settlement_engine.idl.json \
  TrdFx402ZkR3M5vW9aK7nB1pQ2eC8sY6tU4jH7vL9mNp \
  --provider.cluster https://api.mainnet-beta.solana.com

# 2. DynamicTradeEscrow (Update / Initialize IDL on Escrow Program)
anchor idl init -f contracts/verification/solana/dynamic_trade_escrow.idl.json \
  DynSxW8JCy6296toTYrdhJqnoxtMvf3CPmtSSFEyqNnz \
  --provider.cluster https://api.mainnet-beta.solana.com

# 3. AgentPaymentVault
anchor idl init -f contracts/verification/solana/agent_payment_vault.idl.json \
  7oZ16YaazQzN6z5uA1nAZWD9oGUDXyvHwXGJLFYyWi3y \
  --provider.cluster https://api.mainnet-beta.solana.com

# 4. MineralsOracleConsumer
anchor idl init -f contracts/verification/solana/minerals_oracle_consumer.idl.json \
  21ZR1QCyAbNrRLs1iWEkdbNsfCFdJcy6ip9R2JxDbkTL \
  --provider.cluster https://api.mainnet-beta.solana.com
```

---

## 3. Step 2: Solscan Project Verification & Official Label Application

Apply for verified project badge and official logo tags:

1. Visit [Solscan Token & Program Verification Portal](https://solscan.io/verify-token).
2. Attach `contracts/verification/solana/solscan_metadata.json`.
3. Provide Github repo and institutional trade documentation.
