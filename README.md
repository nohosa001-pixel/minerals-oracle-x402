# EV Battery Critical Minerals & Provenance Oracle (`minerals-oracle-x402`)

[![PyPI Version](https://img.shields.io/pypi/v/minerals-oracle-x402.svg?color=blue&style=for-the-badge&logo=pypi&logoColor=white)](https://pypi.org/project/minerals-oracle-x402/)
[![Tests](https://img.shields.io/badge/Tests-119%2F119_Passing-brightgreen?style=for-the-badge&logo=pytest&logoColor=white)](https://github.com/nohosa001-pixel/minerals-oracle-x402)
[![Spec Version](https://img.shields.io/badge/Compliance_Spec-v2.5.0-purple?style=for-the-badge)](GLOBAL_BATTERY_MINERALS_COMPLIANCE_SPEC.md)
[![FastMCP](https://img.shields.io/badge/FastMCP-Model_Context_Protocol-00ffcc?style=for-the-badge&logo=anthropic&logoColor=black)](mcp_tool_spec.json)
[![Polygon Network](https://img.shields.io/badge/Polygon_USDC-x402_Settlement-8247E5?style=for-the-badge&logo=polygon&logoColor=white)](https://polygon.technology)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)

> **Autonomous Machine-to-Machine (M2M) Compliance & On-Chain Battery Passport Oracle for Critical Minerals (Lithium, Nickel, Cobalt, Copper, Silver).**  
> Verifies real-world mining extraction, stoichiometric mass balances, US IRA Section 30D 50% FTA value thresholds, strict Foreign Entity of Concern (FEOC) taint propagation, EU Battery Regulation (2023/1542) & 2028 Downstream CBAM carbon footprints, ASTM B115 HVDC copper grid standards, LBMA TOPCon solar PV silver purity, and issues cryptographic Merkle Root EIP-712 master attestations on Polygon.

---

## 🖥️ Live Web Observatories & Dashboards

* 🇰🇷 **한국어 전용 노드 & 컴플라이언스 관측기**: [http://localhost:8000/ko](http://localhost:8000/ko) (또는 [Cloud Run Live](https://minerals-oracle-x402-212942243360.asia-northeast3.run.app/ko))
* 🌐 **Global English Dashboard & Simulator**: [http://localhost:8000/](http://localhost:8000/) (또는 [Cloud Run Live](https://minerals-oracle-x402-212942243360.asia-northeast3.run.app/))
* 📚 **Interactive Swagger OpenAPI Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
* 📑 **LLM Agent Manifest**: [`/llms.txt`](llms.txt)

---

## ⚡ Key Architectural Capabilities (v2.4.0)

### 1. Composite EV Battery Master Passport Orchestrator (`app/composite_battery_pipeline.py`)
Synthesizes the 3 primary battery critical minerals into a unified cell/pack compliance attestation:
* **Cathode Chemistries**: **NCM 811** (80% Ni, 10% Co, 10% Mn), **NCM 622**, **NCM 523**.
* **US IRA 30D Critical Minerals $3,750 Tax Credit Formula**:
  $$\text{Procurement Value} = (\text{Li Tons} \times \$18,500) + (\text{Ni Tons} \times \$17,000) + (\text{Co Tons} \times \$32,000)$$
  $$\text{FTA Qualifying Ratio} = \frac{\text{Value}_{\text{AUS (FTA)}}}{\text{Value}_{\text{Total}}} \times 100\% \ge 50.0\%$$
* **Strict Zero-Tolerance FEOC Taint Propagation**: If **any** mineral component carries $\ge 25\%$ covered nation (China/Russia/Iran/North Korea) equity or operational control, the entire battery pack is disqualified (`FLAG_COMPOSITE_FEOC_TAINT`).
* **EU Battery Regulation (2023/1542) & CBAM Scope 1-3 Carbon Footprint**:
  * Captive coal power smelting in Indonesian HPAL triggers `FLAG_EU_BATTERY_CBAM_SURCHARGE` (+26.5 kg CO₂e/kWh penalty).
* **Cryptographic Merkle Tree & Polygon EIP-712 Master Signature**:
  $$\text{Merkle Root} = \text{0x} + \text{SHA256}(\text{Leaf}_{\text{Li}} + \text{Leaf}_{\text{Ni}} + \text{Leaf}_{\text{Co}})$$
  Signs typed structured data binding `battery_pack_id`, `chemistry`, `merkle_root`, composite score, and legal disclaimer terms.

---

### 2. Dedicated Provenance Pipelines for Core Minerals

```mermaid
flowchart TD
    subgraph Mining["1. Global Extraction & Geofencing"]
        Li["🇦🇺 Australia (Greenbushes / Pilgangoora)<br/>WA MINEDEX GIS Geofencing"]
        Ni["🇮🇩 Indonesia (IMIP Morowali / IWIP)<br/>Sulawesi/Halmahera Geofencing"]
        Co["🇨🇩 DRC (Kamoto KCC / Tenke / Mutanda)<br/>Katanga Copperbelt Geofencing"]
    end

    subgraph Processing["2. Stoichiometric Mass Balance & Traps"]
        LiProc["Spodumene to LiOH (7.5:1 Yield)<br/>Anti-Transshipment Geofencing"]
        NiProc["Limonite to MHP (31.34:1 Yield)<br/>ESDM SIMBARA NTPN Tax Clear<br/>EU CBAM Coal Smelting Audit"]
        CoProc["Heterogenite to Hydroxide (23.53:1 Yield)<br/>CEEC Barcode Seal Verification<br/>ILO 138/182 Zero Child Labor Audit"]
    end

    subgraph Composite["3. Composite Battery Orchestrator"]
        Master["NCM 811 Pack Synthesis<br/>IRA FTA Value Ratio (>= 50%)<br/>FEOC Taint Propagation (< 25%)<br/>EU Cradle-to-Gate Carbon Footprint"]
    end

    subgraph Attestation["4. Cryptographic Proof & Settlement"]
        Merkle["Merkle Tree Synthesis<br/>sha256(Leaf_Li + Leaf_Ni + Leaf_Co)"]
        Onchain["Polygon EIP-712 Master Signature<br/>x402 0.10 USDC Gasless Settlement"]
    end

    Li --> LiProc --> Master
    Ni --> NiProc --> Master
    Co --> CoProc --> Master
    Master --> Merkle --> Onchain
```

#### 🇦🇺 Australian Spodumene Lithium Pipeline (`app/lithium_pipeline.py`)
* **GIS Geofencing**: Validates WA DMIRS MINEDEX tenement boundaries (e.g. Greenbushes `M01/03`, Pilgangoora `M45/1256`).
* **Stoichiometric Mass Balance**: Enforces strict theoretical yield ratio ($7.5 \pm 0.8\text{t}$ Spodumene concentrate $\rightarrow$ $1.0\text{t}$ Battery-Grade LiOH·H₂O).
* **Defenses**: Defends against Trap 13 (Chinese transshipment relabeling) and Trap 14 (non-linear recovery exaggeration).

#### 🇮🇩 Indonesian Nickel MHP Pipeline (`app/nickel_pipeline.py`)
* **Concession Geofencing**: Monitors Central Sulawesi (IMIP Morowali) and North Maluku (IWIP Weda Bay) mining polygons.
* **Fiscal Verification**: Validates Ministry of Energy (ESDM) SIMBARA NTPN tax receipt codes and Bank Indonesia 30% forex export deposits (DHE BI).
* **EU CBAM & Carbon Duty**: Detects captive coal power plant usage and flags European Carbon Border Adjustment liabilities.

#### 🇨🇩 DRC Cobalt Hydroxide Pipeline (`app/cobalt_pipeline.py`)
* **Artisanal Segregation (Trap 1)**: Blocks uncertified artisanal mining (ASM) co-mingling via Entreprise Générale du Cobalt (EGC) custody validation.
* **CEEC Security Seals**: Cryptographically authenticates Centre d'Expertise (CEEC) tamper-proof barcode export seals.
* **ILO Human Rights Diligence**: Enforces mandatory independent audits for ILO Convention 138 (Minimum Age) and 182 (Worst Forms of Child Labor).

#### 🇨🇱 Chilean Copper Cathode Pipeline (`app/copper_pipeline.py`)
* **Concession Geofencing**: Monitors major porphyry operations (Codelco Chuquicamata, El Teniente, Andina, BHP Escondida, Antofagasta Los Pelambres, Cerro Verde).
* **Smelter Acid Balance (Trap 16)**: Validates sulfuric acid ($H_2SO_4$) reagent supply balance ($\le 5.0\%$ deficit tolerance).
* **Grid & Purity Standard**: Certifies ASTM B115 Grade 1 electrolytic cathode purity ($\ge 99.9935\%$) for AI datacenter HVDC power grids and COCHILCO export clearances.

#### 🇲🇽 Mexican Silver Doré Pipeline (`app/silver_pipeline.py`)
* **Concession Geofencing**: Monitors high-grade silver operations (Endeavour Silver Terronera, Fresnillo, Antamina, Uchucchacua, Los Pelambres).
* **N-Type TOPCon Solar Standard (Trap 16)**: Enforces ultra-pure $\ge 99.99\%$ silver powder certification for next-gen solar PV metallization paste.
* **Security & LBMA Assurance**: Defends against cartel-tainted artisanal extraction and validates LBMA Good Delivery refiner accreditation.

---

### 3. Interactive Web Observatory & Verification Simulator

The built-in browser UI ([`app/static/ko.html`](app/static/ko.html) and [`app/static/index.html`](app/static/index.html)) provides a live 4-tab compliance cockpit:

| Tab | Key Features |
| :--- | :--- |
| 🔋 **NCM 811 Composite Master Passport** | Real-time IRA 30D eligibility, FTA value progress bar, EU Battery Passport approval status, Carbon Footprint gauge, on-chain Merkle Root & EIP-712 JSON terminal |
| 🇦🇺 **Australian Lithium Observatory** | Hard-rock mine selection (Greenbushes, Pilgangoora, Mt Marion), ore feed vs LiOH yield calculation |
| 🇮🇩 **Indonesian Nickel MHP Observatory** | IMIP/IWIP concession verification, ESDM SIMBARA tax receipt verification, captive coal power toggle |
| 🇨🇩 **DRC Cobalt Hydroxide Observatory** | Kamoto KCC/Tenke concession check, CEEC barcode verification, ILO 138/182 child labor audit toggle |

#### One-Click Real-World Scenario Presets
* **✅ Clean Baseline (`clean`)**: Australia Greenbushes + Indonesia Clean IMIP + DRC Kamoto KCC $\rightarrow$ IRA Eligible ($3,750), EU Passport Approved, Low Carbon (51.5 kg CO₂e/kWh).
* **⚠️ FEOC Taint Trap (`feoc`)**: Injects 80% Chinese state ownership into DRC Cobalt $\rightarrow$ Entire battery pack disqualified under FEOC 25% threshold.
* **⚠️ Captive Coal CBAM Trap (`cbam`)**: Injects captive coal power smelting in Indonesia $\rightarrow$ EU CBAM carbon tariff liabilities triggered.
* **❌ Child Labor Trap (`child`)**: Injects uncertified artisanal pit ore in DRC $\rightarrow$ EU Battery Passport immediate rejection.
* **🚨 Trap 15 Tech Defense (`trap15`)**: Evaluates Chinese Mineral Resources Law extraterritorial licensing taint ($>50\%$ SX tech dependency without MOFCOM clearance).
* **⚡ Copper HVDC Grid Ready (`copper`)**: Codelco Chuquicamata copper cathode audit, $H_2SO_4$ acid balance, and ASTM B115 Grade 1 HVDC power grid certification.
* **☀️ Silver TOPCon Solar PV (`silver`)**: Endeavour Silver Terronera doré audit, LBMA Good Delivery, and N-Type TOPCon $\ge 99.99\%$ solar paste verification.

---

## 🤖 Model Context Protocol (FastMCP) Tools

Integrates natively with Claude Desktop, Cursor, Gemini, and autonomous AI agents:

```json
{
  "mcpServers": {
    "minerals-oracle-x402": {
      "command": "python",
      "args": ["-m", "app.mcp_stdio"],
      "env": {
        "ORACLE_API_KEY": "YOUR_AGENT_KEY"
      }
    }
  }
}
```

### Supported MCP Tools:
1. `verify_composite_battery_passport`: Evaluates end-to-end NCM EV battery packs and generates Master Merkle EIP-712 attestations.
2. `verify_lithium_origin`: Verifies Australian hard-rock spodumene extraction and conversion.
3. `verify_nickel_origin`: Verifies Indonesian laterite limonite HPAL MHP provenance and SIMBARA tax clearance.
4. `verify_cobalt_origin`: Verifies DRC Katanga heterogenite cobalt hydroxide provenance, CEEC seals, and child labor audits.
5. `verify_copper_origin`: Verifies Chilean/South American copper cathode provenance, COCHILCO quotas, H2SO4 acid balance, and ASTM B115 HVDC compliance.
6. `verify_silver_origin`: Verifies Mexican/South American silver doré provenance, LBMA certification, N-Type TOPCon solar PV 99.99% purity, and cartel defense.
7. `verify_mineral_compliance`: Legacy 7-pillar compliance audit engine for individual mineral lots.
8. `minerals_submit_agent_feedback`: Zero-fee protocol feedback submission for autonomous agent evolution.

---

## 💳 Autonomous x402 Web3 Settlement on Polygon

All M2M API invocations support micro-payments in USDC on Polygon (Chain ID `137`):

* **Composite Battery Master Verification**: 0.10 USDC (`PricingTier.STANDARD`)
* **Dedicated Mineral Lot Verification**: 0.05 USDC (`PricingTier.LIGHT`)
* **Polygon USDC Address**: `0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359`
* **Treasury Recipient**: `0x255F9991233f86B29dB847c8d5b8CB9915e80dCf`
* **Agent Vault Fast-Path**: Zero-latency verification via pre-funded `X-Agent-Vault-Key` headers.

---

## 🚀 Quick Start & Local Execution

### 1. Clone & Install Dependencies
```bash
git clone https://github.com/nohosa001-pixel/minerals-oracle-x402.git
cd minerals-oracle-x402

python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

pip install -e .
```

### 2. Run Tests (102 Automated Tests)
```bash
# Run with -s flag on Windows
pytest -s tests/
```

### 3. Launch Local Server & Web Observatory
```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
Navigate to:
* **Korean Core Node**: [http://localhost:8000/ko](http://localhost:8000/ko)
* **Global English Node**: [http://localhost:8000/](http://localhost:8000/)
* **API Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 📜 Full Technical Specifications
For full mathematical formulations, threshold constants, legal citations, and EIP-712 type declarations, consult the [Global Battery Minerals Compliance Specification v2.4.0](GLOBAL_BATTERY_MINERALS_COMPLIANCE_SPEC.md).

---

## 📄 License
MIT License. Copyright (c) 2026 Minerals Oracle x402 Project Contributors.
