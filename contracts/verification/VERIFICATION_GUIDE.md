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

### Polygon - Contract A: `AgentPaymentVault.sol`

* **Status**: ✅ **Verified on Polygonscan**
* **Deployed Address**: [`0xb44Bc2Acdd156cE08b549A00a3102e4B01276654`](https://polygonscan.com/address/0xb44Bc2Acdd156cE08b549A00a3102e4B01276654#code)
* **Direct Verification URL**: [https://polygonscan.com/verifyContract?a=0xb44Bc2Acdd156cE08b549A00a3102e4B01276654](https://polygonscan.com/verifyContract?a=0xb44Bc2Acdd156cE08b549A00a3102e4B01276654)
* **Source File**: [`contracts/verification/AgentPaymentVault.flattened.sol`](AgentPaymentVault.flattened.sol)
* **Constructor Arguments**:
  * `_usdcTokenAddress` (Polygon Native USDC): `0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359`
  * `_oracleOperator` (Treasury): `0xA185B43fDD19619f99952AAed6eabf1029bF36a1`
* **ABI-Encoded Constructor Arguments (HEX)**:

```text
0000000000000000000000003c499c542cef5e3811e1192ce70d8cc03d5c3359000000000000000000000000255f9991233f86b29db847c8d5b8cb9915e80dcf
```

---

### Polygon - Contract B: `MineralsOracleConsumer.sol`

* **Status**: ✅ **Verified on Polygonscan**
* **Deployed Address**: [`0x835d01534a5D2e63D52636Fafb1019f889d1E66B`](https://polygonscan.com/address/0x835d01534a5D2e63D52636Fafb1019f889d1E66B#code)
* **Direct Verification URL**: [https://polygonscan.com/verifyContract?a=0x835d01534a5D2e63D52636Fafb1019f889d1E66B](https://polygonscan.com/verifyContract?a=0x835d01534a5D2e63D52636Fafb1019f889d1E66B)
* **Source File**: [`contracts/verification/MineralsOracleConsumer.flattened.sol`](MineralsOracleConsumer.flattened.sol)
* **Constructor Arguments**:
  * `_trustedOracleSigner` (Treasury): `0xA185B43fDD19619f99952AAed6eabf1029bF36a1`
* **ABI-Encoded Constructor Arguments (HEX)**:

```text
000000000000000000000000255f9991233f86b29db847c8d5b8cb9915e80dcf
```

### Polygon - Contract C: `DynamicTradeEscrow.sol`

* **Status**: ✅ **Verified (exact_match)** on Sourcify & Polygonscan Ready
* **Sourcify Verified Badge**: [`https://sourcify.dev/#/lookup/137/0x3A863A2b1018B47FE79041FCDF56efEa3f8b978F`](https://sourcify.dev/#/lookup/137/0x3A863A2b1018B47FE79041FCDF56efEa3f8b978F)
* **Deployed Address**: [`0x3A863A2b1018B47FE79041FCDF56efEa3f8b978F`](https://polygonscan.com/address/0x3A863A2b1018B47FE79041FCDF56efEa3f8b978F#code)
* **Creation Tx**: [`0x2bbc62d2b1d382c081ebd8cf035c1906094f70e973732534987e9adbefd06b51`](https://polygonscan.com/tx/0x2bbc62d2b1d382c081ebd8cf035c1906094f70e973732534987e9adbefd06b51)
* **Direct Verification URL**: [https://polygonscan.com/verifyContract?a=0x3A863A2b1018B47FE79041FCDF56efEa3f8b978F](https://polygonscan.com/verifyContract?a=0x3A863A2b1018B47FE79041FCDF56efEa3f8b978F)
* **Source File**: [`contracts/verification/DynamicTradeEscrow.flattened.sol`](DynamicTradeEscrow.flattened.sol)
* **Constructor Arguments**:
  * `_usdcToken` (Polygon Native USDC): `0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359`
  * `_trustedOracle` (Treasury): `0xA185B43fDD19619f99952AAed6eabf1029bF36a1`
  * `_pythAddress` (Polygon Pyth Network): `0xff1a0f4744e8582DF1aE09D5611b887B6a12925C`
* **ABI-Encoded Constructor Arguments (HEX)**:

```text
0000000000000000000000003c499c542cef5e3811e1192ce70d8cc03d5c3359000000000000000000000000a185b43fdd19619f99952aaed6eabf1029bf36a1000000000000000000000000ff1a0f4744e8582df1ae09d5611b887b6a12925c
```

---

## 3. Base Mainnet (Chain ID: 8453)

### Base - Contract A: `AgentPaymentVault.sol`

* **Deployed Address**: [`0x8ACafCEce0B1BFE140e75614b90FD1307b6f389d`](https://basescan.org/address/0x8ACafCEce0B1BFE140e75614b90FD1307b6f389d#code)
* **Direct Verification URL**: [https://basescan.org/verifyContract?a=0x8ACafCEce0B1BFE140e75614b90FD1307b6f389d](https://basescan.org/verifyContract?a=0x8ACafCEce0B1BFE140e75614b90FD1307b6f389d)
* **Native USDC Address**: `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913`
* **Constructor Arguments (HEX)**:

```text
000000000000000000000000833589fcd6edb6e08f4c7c32d4f71b54bda02913000000000000000000000000255f9991233f86b29db847c8d5b8cb9915e80dcf
```

### Base - Contract B: `MineralsOracleConsumer.sol`

* **Deployed Address**: [`0xe43a9C368808B2dfF139D27789C40A3C8F2282cF`](https://basescan.org/address/0xe43a9C368808B2dfF139D27789C40A3C8F2282cF#code)
* **Direct Verification URL**: [https://basescan.org/verifyContract?a=0xe43a9C368808B2dfF139D27789C40A3C8F2282cF](https://basescan.org/verifyContract?a=0xe43a9C368808B2dfF139D27789C40A3C8F2282cF)
* **Constructor Arguments (HEX)**:

```text
000000000000000000000000255f9991233f86b29db847c8d5b8cb9915e80dcf
```

### Base - Contract C: `DynamicTradeEscrow.sol`

* **Status**: ✅ **Verified (exact_match)** on Sourcify & Basescan Ready
* **Sourcify Verified Badge**: [`https://sourcify.dev/#/lookup/8453/0x54786360Db4582AEC2435E216479FD4ff093CB80`](https://sourcify.dev/#/lookup/8453/0x54786360Db4582AEC2435E216479FD4ff093CB80)
* **Deployed Address**: [`0x54786360Db4582AEC2435E216479FD4ff093CB80`](https://basescan.org/address/0x54786360Db4582AEC2435E216479FD4ff093CB80#code)
* **Creation Tx**: [`0x7768f715ec663550e7f0c553ac9f0d0f1249e25ad73519c28ddae1e28d8b2bd2`](https://basescan.org/tx/0x7768f715ec663550e7f0c553ac9f0d0f1249e25ad73519c28ddae1e28d8b2bd2)
* **Direct Verification URL**: [https://basescan.org/verifyContract?a=0x54786360Db4582AEC2435E216479FD4ff093CB80](https://basescan.org/verifyContract?a=0x54786360Db4582AEC2435E216479FD4ff093CB80)
* **Source File**: [`contracts/verification/DynamicTradeEscrow.flattened.sol`](DynamicTradeEscrow.flattened.sol)
* **Constructor Arguments**:
  * `_usdcToken` (Base Native USDC): `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913`
  * `_trustedOracle` (Treasury): `0xA185B43fDD19619f99952AAed6eabf1029bF36a1`
  * `_pythAddress` (Base Pyth Network): `0x8250f4aF4B972684F7b336503E2D6dFeDeB72416`
* **Constructor Arguments (HEX)**:

```text
000000000000000000000000833589fcd6edb6e08f4c7c32d4f71b54bda02913000000000000000000000000a185b43fdd19619f99952aaed6eabf1029bf36a10000000000000000000000008250f4af4b972684f7b336503e2d6dfedeb72416
```

---

## 4. Arbitrum One (Chain ID: 42161)

### Arbitrum - Contract A: `AgentPaymentVault.sol`

* **Deployed Address**: [`0x8ACafCEce0B1BFE140e75614b90FD1307b6f389d`](https://arbiscan.io/address/0x8ACafCEce0B1BFE140e75614b90FD1307b6f389d#code)
* **Direct Verification URL**: [https://arbiscan.io/verifyContract?a=0x8ACafCEce0B1BFE140e75614b90FD1307b6f389d](https://arbiscan.io/verifyContract?a=0x8ACafCEce0B1BFE140e75614b90FD1307b6f389d)
* **Native USDC Address**: `0xaf88d065e77c8cC2239327C5EDb3A432268e5831`
* **Constructor Arguments (HEX)**:

```text
000000000000000000000000af88d065e77c8cc2239327c5edb3a432268e5831000000000000000000000000255f9991233f86b29db847c8d5b8cb9915e80dcf
```

### Arbitrum - Contract B: `MineralsOracleConsumer.sol`

* **Deployed Address**: [`0xe43a9C368808B2dfF139D27789C40A3C8F2282cF`](https://arbiscan.io/address/0xe43a9C368808B2dfF139D27789C40A3C8F2282cF#code)
* **Direct Verification URL**: [https://arbiscan.io/verifyContract?a=0xe43a9C368808B2dfF139D27789C40A3C8F2282cF](https://arbiscan.io/verifyContract?a=0xe43a9C368808B2dfF139D27789C40A3C8F2282cF)
* **Constructor Arguments (HEX)**:

```text
000000000000000000000000255f9991233f86b29db847c8d5b8cb9915e80dcf
```

### Arbitrum - Contract C: `DynamicTradeEscrow.sol`

* **Status**: ✅ **Verified (exact_match)** on Sourcify & Arbiscan Ready
* **Sourcify Verified Badge**: [`https://sourcify.dev/#/lookup/42161/0x54786360Db4582AEC2435E216479FD4ff093CB80`](https://sourcify.dev/#/lookup/42161/0x54786360Db4582AEC2435E216479FD4ff093CB80)
* **Deployed Address**: [`0x54786360Db4582AEC2435E216479FD4ff093CB80`](https://arbiscan.io/address/0x54786360Db4582AEC2435E216479FD4ff093CB80#code)
* **Creation Tx**: [`0x460da830800ef8b8c404b6b1aa81d33885f8499721cda6699e85ac501e7954a8`](https://arbiscan.io/tx/0x460da830800ef8b8c404b6b1aa81d33885f8499721cda6699e85ac501e7954a8)
* **Direct Verification URL**: [https://arbiscan.io/verifyContract?a=0x54786360Db4582AEC2435E216479FD4ff093CB80](https://arbiscan.io/verifyContract?a=0x54786360Db4582AEC2435E216479FD4ff093CB80)
* **Source File**: [`contracts/verification/DynamicTradeEscrow.flattened.sol`](DynamicTradeEscrow.flattened.sol)
* **Constructor Arguments**:
  * `_usdcToken` (Arbitrum Native USDC): `0xaf88d065e77c8cC2239327C5EDb3A432268e5831`
  * `_trustedOracle` (Treasury): `0xA185B43fDD19619f99952AAed6eabf1029bF36a1`
  * `_pythAddress` (Arbitrum Pyth Network): `0xff1a0f4744e8582DF1aE09D5611b887B6a12925C`
* **Constructor Arguments (HEX)**:

```text
000000000000000000000000af88d065e77c8cc2239327c5edb3a432268e5831000000000000000000000000a185b43fdd19619f99952aaed6eabf1029bf36a1000000000000000000000000ff1a0f4744e8582df1ae09d5611b887b6a12925c
```

---

## 5. Automated Verification Script

Run the automated verification helper:

```bash
# Verify or print constructor payloads
python scripts/verify_contracts.py --chain polygon
python scripts/verify_contracts.py --chain base
python scripts/verify_contracts.py --chain arbitrum
```
