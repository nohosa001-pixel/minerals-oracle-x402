# Smart Contract Verification & Public Explorer Guide

This guide provides everything required to verify and publicly display **`AgentPaymentVault.sol`** and **`MineralsOracleConsumer.sol`** on block explorers (**Polygonscan**, **BaseScan**, **Arbiscan**).

---

## 1. Quick Verification Parameters

| Parameter | Value |
| :--- | :--- |
| **Solidity Compiler Version** | `v0.8.20+commit.a1b79de6` |
| **Open Source License Type** | `MIT License (MIT)` |
| **Optimization** | `Yes` |
| **Optimization Runs** | `200` |
| **EVM Version** | `default` (or `shanghai` / `paris`) |

---

## 2. Polygon Mainnet (Chain ID: 137)

### Contract A: `AgentPaymentVault.sol`

* **Status**: ✅ **Verified on Polygonscan**
* **Deployed Address**: [`0xb44Bc2Acdd156cE08b549A00a3102e4B01276654`](https://polygonscan.com/address/0xb44Bc2Acdd156cE08b549A00a3102e4B01276654#code)
* **Direct Verification URL**: [https://polygonscan.com/verifyContract?a=0xb44Bc2Acdd156cE08b549A00a3102e4B01276654](https://polygonscan.com/verifyContract?a=0xb44Bc2Acdd156cE08b549A00a3102e4B01276654)
* **Source File**: [`contracts/verification/AgentPaymentVault.flattened.sol`](AgentPaymentVault.flattened.sol)
* **Constructor Arguments**:
  * `_usdcTokenAddress` (Polygon Native USDC): `0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359`
  * `_oracleOperator` (Treasury): `0x255F9991233f86B29dB847c8d5b8CB9915e80dCf`
* **ABI-Encoded Constructor Arguments (HEX)**:

```text
0000000000000000000000003c499c542cef5e3811e1192ce70d8cc03d5c3359000000000000000000000000255f9991233f86b29db847c8d5b8cb9915e80dcf
```

---

### Contract B: `MineralsOracleConsumer.sol`

* **Status**: ✅ **Verified on Polygonscan**
* **Deployed Address**: [`0x835d01534a5D2e63D52636Fafb1019f889d1E66B`](https://polygonscan.com/address/0x835d01534a5D2e63D52636Fafb1019f889d1E66B#code)
* **Direct Verification URL**: [https://polygonscan.com/verifyContract?a=0x835d01534a5D2e63D52636Fafb1019f889d1E66B](https://polygonscan.com/verifyContract?a=0x835d01534a5D2e63D52636Fafb1019f889d1E66B)
* **Source File**: [`contracts/verification/MineralsOracleConsumer.flattened.sol`](MineralsOracleConsumer.flattened.sol)
* **Constructor Arguments**:
  * `_trustedOracleSigner` (Treasury): `0x255F9991233f86B29dB847c8d5b8CB9915e80dCf`
* **ABI-Encoded Constructor Arguments (HEX)**:

```text
000000000000000000000000255f9991233f86b29db847c8d5b8cb9915e80dcf
```

---

## 3. Base Mainnet (Chain ID: 8453)

### Contract A: `AgentPaymentVault.sol`
* **Deployed Address**: [`0x8ACafCEce0B1BFE140e75614b90FD1307b6f389d`](https://basescan.org/address/0x8ACafCEce0B1BFE140e75614b90FD1307b6f389d#code)
* **Direct Verification URL**: [https://basescan.org/verifyContract?a=0x8ACafCEce0B1BFE140e75614b90FD1307b6f389d](https://basescan.org/verifyContract?a=0x8ACafCEce0B1BFE140e75614b90FD1307b6f389d)
* **Native USDC Address**: `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913`
* **Constructor Arguments (HEX)**:
```text
000000000000000000000000833589fcd6edb6e08f4c7c32d4f71b54bda02913000000000000000000000000255f9991233f86b29db847c8d5b8cb9915e80dcf
```

### Contract B: `MineralsOracleConsumer.sol`
* **Deployed Address**: [`0xe43a9C368808B2dfF139D27789C40A3C8F2282cF`](https://basescan.org/address/0xe43a9C368808B2dfF139D27789C40A3C8F2282cF#code)
* **Direct Verification URL**: [https://basescan.org/verifyContract?a=0xe43a9C368808B2dfF139D27789C40A3C8F2282cF](https://basescan.org/verifyContract?a=0xe43a9C368808B2dfF139D27789C40A3C8F2282cF)
* **Constructor Arguments (HEX)**:
```text
000000000000000000000000255f9991233f86b29db847c8d5b8cb9915e80dcf
```

---

## 4. Arbitrum One (Chain ID: 42161)

### Contract A: `AgentPaymentVault.sol`
* **Deployed Address**: [`0x8ACafCEce0B1BFE140e75614b90FD1307b6f389d`](https://arbiscan.io/address/0x8ACafCEce0B1BFE140e75614b90FD1307b6f389d#code)
* **Direct Verification URL**: [https://arbiscan.io/verifyContract?a=0x8ACafCEce0B1BFE140e75614b90FD1307b6f389d](https://arbiscan.io/verifyContract?a=0x8ACafCEce0B1BFE140e75614b90FD1307b6f389d)
* **Native USDC Address**: `0xaf88d065e77c8cC2239327C5EDb3A432268e5831`
* **Constructor Arguments (HEX)**:
```text
000000000000000000000000af88d065e77c8cc2239327c5edb3a432268e5831000000000000000000000000255f9991233f86b29db847c8d5b8cb9915e80dcf
```

### Contract B: `MineralsOracleConsumer.sol`
* **Deployed Address**: [`0xe43a9C368808B2dfF139D27789C40A3C8F2282cF`](https://arbiscan.io/address/0xe43a9C368808B2dfF139D27789C40A3C8F2282cF#code)
* **Direct Verification URL**: [https://arbiscan.io/verifyContract?a=0xe43a9C368808B2dfF139D27789C40A3C8F2282cF](https://arbiscan.io/verifyContract?a=0xe43a9C368808B2dfF139D27789C40A3C8F2282cF)
* **Constructor Arguments (HEX)**:
```text
000000000000000000000000255f9991233f86b29db847c8d5b8cb9915e80dcf
```

---

## 4. Automated Verification Script

Run the automated verification helper:

```bash
# Verify or print constructor payloads
python scripts/verify_contracts.py --chain polygon
python scripts/verify_contracts.py --chain base
python scripts/verify_contracts.py --chain arbitrum
```
