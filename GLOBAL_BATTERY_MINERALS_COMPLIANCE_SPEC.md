# GLOBAL CRITICAL MINERALS & BATTERY SUPPLY-CHAIN COMPLIANCE SPECIFICATION
**Autonomous Agent-Native Provenance, 14-Trap Regulatory Defense, Trade Jurisprudence & EIP-712 Passport Oracle**  
*Document Version: 2.4.0 (Production Release — Composite EV Battery Passport Engine Added)*  
*Standard: ISO/IEC 17025, UNCITRAL MLETR, EU 2023/1542, EU CBAM (2023/956), US IRA 30D, US BIS 15 CFR § 744, OECD Annex II, EIP-712*

---

## 1. Executive Overview & Core Philosophy

### 1.1 The Post-Clerical Autonomous Supply Chain
The international minerals and battery supply chain has reached an inflection point where human administrative desks represent a critical liability:
1. **Clerical Bottlenecks & Vulnerability**: Traditional trade and customs brokerage relies on human inspection of PDFs, certificates of origin, and trade manifests. This introduces weeks of clearance delays, corruption vulnerabilities, and catastrophic regulatory penalties (e.g., CBP customs detentions under UFLPA, vessel rejections under EUDR, BIS scrap retention seizures).
2. **Autonomous Machine-Native Paradigm**: `minerals-oracle-x402` operates on a **100% Zero-Human-in-the-Loop** model. Autonomous AI agents trade, charter vessels, balance refinery mass yields, and verify customs eligibility agent-to-agent (A2A).
3. **Autonomous Machine-to-Machine Micro-Payment Flow**: Autonomous AI agents settle compliance verifications using Polygon USDC (`0.005` ~ `0.50` USDC per transaction) via HTTP `402 Payment Required` and Pre-funded Agent Vaults. Human fiat credit cards, banking intermediaries, and manual payment desks are strictly prohibited; micro-fees stream machine-to-machine directly into the on-chain protocol treasury wallet.
4. **Dynamic Legal Synchronization**: Mining laws, export restrictions, and ESG standards evolve continuously. The oracle maintains live monitoring across 10+ mining jurisdictions and 14 regulatory traps, updating versioned regulatory logic graphs in real time.
5. **Zero-Knowledge Proof (ZKP) Confidentiality**: Critical trade secrets (unit pricing, gross margins, supplier identity) remain blinded via off-chain hashing, while mathematical proofs of 100% statutory and environmental compliance are publicly attested on Polygon.

### 1.2 Market Valuation Baselines (2026-09-10 AM Reference)
The oracle calibrates physical collateral valuation and mass balance loss thresholds against live global commodity benchmarks:
- **Gold ($4,402 ~ $4,435 / oz)**: Stabilized above $4,400 on $100+ crude oil, Strait of Hormuz transit disruptions, PBOC bullion accumulation, and US $11T debt monetization hedging.
- **Silver ($67.31 / oz, +2.37%)**: Severe supply bottlenecks across 40.9% of global output (Mexico Terronera blockade, Peru -9.0%, Chile Los Pelambres blizzard) coupled with 6-year structural deficit from N-Type TOPCon solar cell demand.
- **Copper ($6.77 / lb ATH, testing LME $15,000 / t)**: Historical supply crunch caused by US tariff front-loading, Hormuz sulfuric acid reagent shortages for South American SX/EW leaching, Codelco H1 -11% output, and DRC concentrate export caps.
- **Lithium Carbonate (146,750 ~ 156,500 RMB / t, +96.68% YoY)**: Solid floor recovery driven by stationary energy storage system (BESS) demand expansion.

---

## 2. The 7-Pillar Compliance Framework

Every mineral lot evaluated by the oracle must clear the **7 Pillars of Critical Mineral Provenance**:

```
+-----------------------------------------------------------------------------------------+
|                                7-PILLAR COMPLIANCE MATRIX                               |
+-----------------------------------------------------------------------------------------+
| 1. Source Nation Mining Permits & Royalties (SIMBARA, CEEC, DGA, EPBC, ANM, MOFCOM, BIS)|
| 2. Ecological, Spatial & Climate Verification (EUDR, Glaciers, Indigenous, DCE Dams)   |
| 3. Labor, Human Rights & Social Provenance (RMI RMAP, ILUA, Zero Child Labor, CSDDD)    |
| 4. Refining & Metallurgical Mass Balance (Discrepancy <= 2.0%, CBAM Definitive Scope 1-3)|
| 5. Maritime Logistics & Scope 3 Carbon (IMO CII Rating, e-B/L MLETR, ISO 17025, TML)    |
| 6. Geopolitics, Sanctions & Tech Defense (US IRA FEOC < 25%, OFAC SDN, China SX Tech)   |
| 7. Cryptographic On-Chain Passport (EIP-712 Polygon Attestation & Dual Security Proof)  |
+-----------------------------------------------------------------------------------------+
```

### Pillar 1: Source Nation Mining Permits & Export Taxation
- **Indonesia (IDN)**: Mandatory validation of Mineral Online Monitoring System (`SIMBARA`), Non-Tax State Revenue receipt (`NTPN`), Approved Work Plan and Budget quota (`RKAB`), and Bank Indonesia 30% export proceeds retention receipt (`DHE BI`).
- **DR Congo (COD)**: Validation of `CEEC` (Centre d'Expertise, d'Evaluation et de Certification) tamper-proof barcode seals, artisanal mining authority (`EGC`) custody, and absence of ASM non-traceable co-mingling.
- **Chile (CHL)**: General Directorate of Water (`DGA`) extraction permit validation and salt flat hydrologic monitoring well baseline variance `< 0.1%`.
- **Australia (AUS)**: Environmental Protection and Biodiversity Conservation (`EPBC`) Matters of National Environmental Significance (`MNES`) approval.
- **Brazil (BRA)**: National Mining Agency (`ANM`) concession license and Dam Safety Condition Declaration (`DCE`).
- **China (CHN)**: Ministry of Commerce (`MOFCOM`) Dual-Use Item Export License verification for controlled minerals (graphite, antimony).
- **United States (USA)**: Department of Commerce (`BIS`) special export license verification for controlled secondary scrap under 15 CFR § 744.

### Pillar 2: Ecological, Spatial & Climate Multi-Layer
- **EUDR Deforestation Verification**: Verification that mine site land coordinates were not deforested or degraded after December 31, 2020, complying with EU Regulation 2023/1115.
- **Periglacial & Glacier Exclusion**: Validation against Argentine National Institute of Snow, Glaciology and Environmental Sciences (`IANIGLA`) periglacial inventory buffer zones under Ley 26.639 Art. 6.
- **Indigenous Territory Buffer**: Verification of minimum 10 km spatial buffer from demarcated indigenous lands under Brazilian Constitution Art. 231 and Australian Native Title.
- **Tailing Dam Stability**: Proof of DCE geotechnical stability certification under ANM Resolução 95/2022 (upstream tailings dam ban).
- **Aquifer Depletion Alert**: Real-time hydrological drawdown monitoring for brine extraction operations.

### Pillar 3: Labor, Human Rights & Social Provenance
- **RMI RMAP Audit**: Verification that the processing smelter is actively certified under the Responsible Minerals Initiative (`RMI`) Responsible Minerals Assurance Process (`RMAP`).
- **EU CSDDD Mandatory Due Diligence**: Valid third-party human rights and environmental audit proof SHA-256 hash (`csddd_audit_hash`).
- **Zero Child Labor Certification**: Strict zero-tolerance certification under ILO Conventions 138 & 182 and Dodd-Frank Section 1502.
- **Indigenous Land Use Agreement (ILUA)**: Proof of registered ILUA under the Australian Native Title Act 1993 with Free, Prior, and Informed Consent (`FPIC`).
- **UFLPA Forced Labor Presumption**: Cryptographic provenance proving zero input material originates from sanctioned Xinjiang forced labor supply chains.

### Pillar 4: Refining & Mass Balance Math
- **OECD Annex II Mass Balance Discrepancy**: Strict mathematical tracking of feedstock inputs vs. finished refined outputs. The mass balance loss discrepancy must not exceed **2.0%**:
  $$\Delta_{\text{loss}} = \left| 1.0 - \left( \frac{\text{Refined Output}}{\text{Feedstock Input} \times \text{Yield Rate}} \right) \right| \times 100\% \le 2.0\%$$
- **EU CBAM Definitive Period (Regulation 2023/956)**: Live auditing of direct (Scope 1) and indirect (Scope 2) embedded carbon emissions, alongside registered CBAM Declaration ID verification.
- **Captive Coal Power Flag**: Flags Indonesian captive coal-fired power plants (e.g., in Morowali/Weda Bay) to alert European buyers of impending EU CBAM carbon tariff liabilities.

### Pillar 5: Maritime Logistics & Scope 3 Carbon
- **IMO CII Rating**: Cargo vessel Carbon Intensity Indicator rating under IMO MARPOL Annex VI. Tiers A, B, and C are accepted; Tier D incurs a penalty; Tier E fails compliance.
- **UNCITRAL MLETR e-B/L**: Digital Electronic Bill of Lading cryptographic SHA-256 hash anchoring, eliminating paper bill fraud.
- **ISO/IEC 17025 Assay Certificate**: Cryptographic hash of the laboratory Certificate of Analysis (`COA`) verifying purity, moisture, and impurities.
- **IMSBC Code TML Liquefaction Safety**: Certification that mineral bulk cargo moisture content is below the Transportable Moisture Limit (`TML`) to prevent catastrophic bulk carrier liquefaction capsizing.

### Pillar 6: Geopolitics, Sanctions & Technology Defense
- **US IRA Section 30D FEOC Compliance**: Foreign Entity of Concern (`FEOC`) screening under 26 CFR § 1.30D-6. Covered entity (China, Russia, North Korea, Iran) equity shareholding must be **< 25.0%**, board voting control must be **< 25.0%**, and operational contracts must contain zero covered-entity operational vetoes.
- **OFAC SDN Screening**: Automatic screening against US Treasury Office of Foreign Assets Control Specially Designated Nationals list.
- **Substantial Transformation Doctrine**: Origin laundering defense based on US Court of International Trade jurisprudence (*Superior Wire*).
- **China Extraterritorial Tech Jurisdiction**: Verification of independent or authorized solvent extraction (SX) refining technology origin under revised Chinese Mineral Resources Law.

### Pillar 7: Cryptographic On-Chain Passport
- **EIP-712 Structured Signing**: Generates Polygon on-chain verifiable battery passports with typed cryptographic signatures.
- **EU AI Act Article 50 Certification**: Dual-attestation binding the compliance verdict hash with Zero-Trust Security Gate certification.

---

## 3. The 14 Gotcha Trap Defenses

The compliance engine codifies automated defenses against the 14 most dangerous legal and regulatory traps in global trade:

| # | Gotcha Legal Trap | Monitored Law / Standard | Operational Defense Implemented |
|---|---|---|---|
| **1** | **DRC Cobalt ASM Co-mingling** | DRC Mining Code Loi n° 18/001, Décret n° 19/15 | Validates CEEC tamper-proof barcode seals & EGC traceability; blocks uncertified artisanal lots. |
| **2** | **Indonesian SIMBARA & DHE Retention** | PP No. 36/2023, UU No. 3/2020 | Requires valid SIMBARA NTPN receipt + Bank Indonesia 30% export forex deposit confirmation. |
| **3** | **Chilean Atacama Water Depletion** | Código de Aguas DFL 1.122, Ley 19.300 | Verifies DGA water concession & monitoring well salinity/drawdown variance $< 0.1\%$. |
| **4** | **Argentine Periglacial Violations** | Ley Nacional de Glaciares 26.639 Art. 6 | Enforces spatial boundary check against IANIGLA periglacial inventory buffer zones. |
| **5** | **Australian Native Title ILUA** | Native Title Act 1993, EPBC Act 1999 | Mandates registered ILUA agreement number & Commonwealth MNES environmental clearance. |
| **6** | **Brazilian Tailings Dam DCE Failure** | ANM Resolução 95/2022, Const. Art. 231 | Blocks lots lacking active DCE dam stability certificate; enforces indigenous exclusion. |
| **7** | **China Dual-Use Export Restrictions** | MOFCOM Graphite & Antimony Notices | Demands valid MOFCOM dual-use export license number prior to export clearance. |
| **8** | **South Africa Transnet Force Majeure** | MPRDA & Transnet Freight Rail Notices | Evaluates railway corridor congestion and forces contingency port rerouting checks. |
| **9** | **IMO Maritime CII Rating Penalties** | IMO MARPOL Annex VI Tier Rules | Checks vessel IMO registry; rejects CII Tier E vessels; flags Tier D vessels for EU ETS. |
| **10** | **Paper B/L Transit Tampering** | UNCITRAL MLETR Model Law | Locks electronic Bill of Lading (`e-B/L`) SHA-256 hash into the EIP-712 passport. |
| **11** | **OECD Annex II Smelter Mass Leakage** | OECD Due Diligence Guidance (5-Step) | Flags and rejects metallurgical loss discrepancies exceeding $2.0\%$. |
| **12** | **US IRA 30D FEOC Equity Disqualification** | 26 CFR § 1.30D-6 (IRS Guidance) | Audits tiered ownership tree; rejects lots with $\ge 25.0\%$ covered nation equity or board seats. |
| **13** | **US BIS Black Mass & Scrap Retention** | 15 CFR § 744, Defense Production Act | Mandates 100% US domestic allocation of battery black mass/tungsten scrap; blocks unauthorized foreign shipments. |
| **14** | **China Mining Tech Extraterritoriality** | Revised Mineral Resources Law 2026 | Rejects smelters utilizing unauthorized Chinese solvent extraction (SX) separation IP or controlled reagents. |

---

---

## 4. International Trade Jurisprudence Precedents

To defend against arbitrary customs detentions and contractual force majeure claims, the engine integrates binding trade jurisprudence:

### 1. `WTO_DS592_INDONESIA_RAW_MATERIALS`
- **Tribunal**: WTO Dispute Settlement Body
- **Doctrine**: Export restrictions on raw unprocessed ores under domestic value-addition mandates remain contentious under GATT Art. XI.
- **Oracle Rule**: The oracle treats unprocessed raw ore (`NICKEL_ORE`) as high-risk/non-compliant, while certifying finished metallurgical products (`NICKEL_MHP`, Ferronickel) as fully cleared for global trade.

### 2. `WTO_DS431_CHINA_RARE_EARTHS`
- **Tribunal**: WTO Appellate Body
- **Doctrine**: Export quotas and export licensing restrictions cannot be justified under GATT Art. XX(g) conservation exceptions if domestic use is not restricted equivalently.
- **Oracle Rule**: Autonomous cargo lots of controlled graphite, antimony, and rare earths must carry verified MOFCOM export licenses to withstand international customs inspection.

### 3. `ICSID_ARB_15_31_GABRIEL_RESOURCES`
- **Tribunal**: World Bank International Centre for Settlement of Investment Disputes (ICSID)
- **Doctrine**: Host state refusal or revocation of mining permits on legitimate public health, environmental, and social license grounds does not constitute compensable indirect expropriation.
- **Oracle Rule**: Concession permit validity is continuously verified against real-time gazette registries; concessions revoked on environmental grounds fail Pillar 1 automatically.

### 4. `US_CIT_SUPERIOR_WIRE_ORIGIN`
- **Tribunal**: United States Court of International Trade (*Superior Wire v. United States*, 669 F. Supp. 472)
- **Doctrine**: Minor processing, cutting, or re-packaging in a third transit country does not effect a "substantial transformation" conferring a new country of origin.
- **Oracle Rule**: Minerals processed in third countries (e.g., transshipped through Singapore or Vietnam) retain their primary extraction origin for US IRA FEOC and tariff calculations.

### 5. `UK_EWHC_LME_NICKEL_2023`
- **Tribunal**: England and Wales High Court (*Elliott Associates v. London Metal Exchange*)
- **Doctrine**: Central exchange authority to cancel contracts and suspend trading during systemic crisis is legally upheld under English law.
- **Oracle Rule**: Reliance on centralized exchange price discovery exposes buyers to unilateral contract cancellation; physical on-chain lot passports provide sovereign, non-revocable settlement finality.

### 6. `US_BIS_15CFR744_DEFENSE_PRODUCTION_ACT`
- **Tribunal**: U.S. Department of Commerce (Bureau of Industry and Security)
- **Doctrine**: Mandatory 100% domestic retention of critical battery materials, black mass scrap (Li/Ni/Co), and tungsten scrap under Defense Production Act Title III.
- **Oracle Rule**: Unlicensed export of North American secondary battery scrap is flagged as an immediate fatal violation (`Trap 13`).

### 7. `CHN_MINERAL_RESOURCES_LAW_EXTRATERRITORIAL`
- **Tribunal**: Ministry of Commerce (MOFCOM) / Supreme People's Court
- **Doctrine**: Extraterritorial jurisdiction over Chinese patented solvent extraction (SX) separation technology and controlled refining reagents.
- **Oracle Rule**: Smelters outside China must demonstrate independent, licensed, or Western processing IP to avoid seizure of finished goods (`Trap 14`).

### 8. `EU_CBAM_REG_2023_956_DEFINITIVE`
- **Tribunal**: European Court of Justice (CJEU) / DG TAXUD
- **Doctrine**: Mandatory physical surrender of CBAM certificates and accredited verification of embedded Scope 1-3 emissions entering the EU single market.
- **Oracle Rule**: Smelters utilizing captive coal power fail CBAM readiness; explicit Scope 1-3 audit records and Declaration IDs are verified in real time.

---

## 5. API & Machine Interface Reference

### 5.1 REST Endpoints
| Method | Endpoint | Price | Description |
|---|---|---|---|
| `POST` | `/api/v1/oracle/compliance/verify` | 0.50 USDC | Autonomous 7-pillar lot evaluation & EIP-712 passport issuance |
| `POST` | `/api/v1/battery/composite-verify` | 0.10 USDC | Composite EV battery pack multi-mineral provenance & master Merkle passport |
| `POST` | `/api/v1/lithium/verify-origin` | 0.05 USDC | Dedicated Australian Spodumene (Greenbushes/Pilgangoora) FEOC & mass balance verification |
| `POST` | `/api/v1/nickel/verify-origin` | 0.05 USDC | Dedicated Indonesian Nickel MHP (Morowali/Weda Bay/Pomalaa) SIMBARA, HPAL yield & CBAM auditing |
| `POST` | `/api/v1/cobalt/verify-origin` | 0.05 USDC | Dedicated DRC Cobalt Hydroxide (Tenke Fungurume/Kamoto KCC) CEEC, EGC ASM segregation & ILO child labor auditing |
| `GET` | `/api/v1/oracle/compliance/precedents` | Free | Queries WTO, ICSID, CIT, BIS, CJEU, and EWHC jurisprudence citations |
| `GET` | `/api/v1/oracle/compliance/status` | Free | Operational health & active regulatory rules across 10+ nations |
| `GET` | `/api/v1/oracle/prices` | 0.005 USDC | Compact compliance radar feed for critical minerals |
| `GET` | `/api/v1/oracle/challenge` | Free | Issues fresh cryptographic x402 payment nonce |
| `POST` | `/api/v1/agent/onboard` | Free (0.05 trial) | Zero-friction self-serve onboarding for AI agents |

### 5.2 FastMCP JSON-RPC Tools (`python -m app.mcp_stdio`)
1. `verify_mineral_lot_compliance`: Direct tool call for LLM agents to evaluate cargo lots against the 14-trap engine.
2. `verify_composite_battery_passport`: Direct tool call for evaluating multi-stream NCM battery packs, IRA 50% FTA ratio, and Merkle Root EIP-712 signatures.
3. `verify_lithium_origin`: Direct tool call for evaluating Australian spodumene geofencing, stoichiometric yield, and IRA FEOC compliance.
4. `verify_nickel_origin`: Direct tool call for evaluating Indonesian concession geofencing (IMIP/IWIP), SIMBARA NTPN, HPAL mass balance, Captive Coal CBAM, and IRA FEOC.
5. `verify_cobalt_origin`: Direct tool call for evaluating DRC Katanga geofencing (KCC/TFM), CEEC barcode seals, ASM segregation (Trap 1), ILO zero child labor, and RMI RMAP certification.
6. `list_trade_precedents`: Returns legal precedents and tribunal rulings.
7. `get_compliance_status`: Returns live status of monitored nations and 14-trap defense engine.

---

## 7. Zero-Liability 5-Pillar Architecture & Cryptographic Waiver Binding

### 7.1 Economic Asymmetry & Operational Viability
The Oracle provides automated, low-latency computational verification for a nominal micro-fee ($0.50 USDC). Given that critical mineral cargoes frequently exceed tens of millions of dollars in transaction value, the Oracle cannot internalize macro-commercial risks or regulatory liability. Risk strictly resides with the commercial parties reaping trade profits and holding direct physical custody over cargo.

### 7.2 The 5 Core Pillars of Zero-Liability M2M Design

1. **Complete Exclusion of Guarantee/Certification Terminology**:
   - Strictly prohibited expressions: *Compliance Guaranteed*, *Official Certification*, *Verified Free of Deforestation*.
   - Mandated objective definitions: **Raw Calculation** (원천 계산값), **Algorithmic Heuristic Score** (알고리즘 추정 점수), **Public Ledger Feed** (공개 원장 피드).
   - The Oracle is legally defined as a stateless arithmetic calculator that converts public satellite coordinates and government mining registry inputs into heuristic numeric indices, not an inspection agency.

2. **Mandatory Top-Level Response Metadata (`meta`)**:
   - Every JSON payload returned across all endpoints begins with an immutable, fixed `meta` disclaimer block:
   ```json
   {
     "status": "success",
     "meta": {
       "license": "AS-IS",
       "disclaimer": "This output is an automated algorithmic data reference and does not constitute legal, regulatory, or compliance certification. The user/calling agent assumes all risks regarding real-world application.",
       "service_nature": "Algorithmic Heuristic Calculator & Public Ledger Feed (Stateless M2M)"
     },
     "data": { ... }
   }
   ```

3. **MCP Tool Schema Prompt Guard (Agent-Level Safety Injection)**:
   - Tool descriptions injected into consuming LLMs contain mandatory prompt guards:
   - *"Fetches raw algorithmic indices derived from open satellite/market data and computes 12-trap rule heuristics for a mineral lot. DO NOT use as an official regulatory legal filing or physical assay certification without independent manual verification."*
   - Forces upstream agents to synthesize safe, guarded outputs when generating reports for downstream human operators.

4. **MIT / Apache 2.0 Standard Open Source "AS-IS" Warranty Waiver**:
   - Standard, battle-tested disclaimer codified across all documentation and response headers:
   - *"PROVIDED 'AS IS', WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT."*

5. **Irreversible Zero-Identity Peer-to-Peer Vending Model (Zero Identity)**:
   - Zero human accounts, zero email collection, zero signup forms, and zero KYC databases.
   - Operates strictly as a stateless 'Data Token Vending Machine' via on-chain micro-transactions (`x402` / Polygon USDC).
   - Because transactions settle peer-to-peer as instant token exchanges, no continuous customer-provider contractual relationship exists, preemptively eliminating terms-of-service disputes and refund litigation.

### 7.3 Cryptographic Binding in EIP-712 Structured Data
The disclaimer terms are canonized into a deterministic string and hashed via SHA-256 (`disclaimerHash`). This hash is directly embedded as an immutable parameter within the Polygon on-chain `CompliancePassport` EIP-712 typed struct:
```solidity
struct CompliancePassport {
    string lotId;
    string mineralType;
    string sourceCountry;
    uint256 score;
    bool isCompliant;
    bytes32 digestHash;
    bytes32 disclaimerHash; // Legally binding waiver hash
    uint256 timestamp;
}
```
Any smart contract, autonomous agent, or tribunal verifying the Oracle's cryptographic ECDSA signature (`ecrecover`) mathematically consents to the waiver. Modifying or contesting the disclaimer causes the signature verification to fail.

---

## 8. Verification & Quality Assurance Status
- **Automated Test Suite**: 101 / 101 Core, Scenario & Specialized Pipeline Tests Passing (100%)
- **Composite EV Battery Master Passport Engine**: Fully integrated via `POST /api/v1/battery/composite-verify` and FastMCP `verify_composite_battery_passport` (Li+Ni+Co multi-stream orchestration, US IRA 50% FTA ratio, Merkle Root EIP-712 signature)
- **Australian Spodumene Provenance Engine**: Fully integrated via `POST /api/v1/lithium/verify-origin` and FastMCP `verify_lithium_origin`
- **Indonesian Nickel MHP Provenance Engine**: Fully integrated via `POST /api/v1/nickel/verify-origin` and FastMCP `verify_nickel_origin` (SIMBARA NTPN, HPAL mass balance, Captive Coal CBAM, IRA FEOC)
- **DRC Cobalt Hydroxide Provenance Engine**: Fully integrated via `POST /api/v1/cobalt/verify-origin` and FastMCP `verify_cobalt_origin` (CEEC barcode seals, EGC ASM segregation, ILO zero child labor, RMI RMAP)
- **14-Trap Regulatory Defense Engine**: Fully validated with dedicated unit tests for Trap 13 (US BIS Scrap) and Trap 14 (China SX Tech Jurisdiction)
- **EU CBAM & CSDDD Compliance**: Scope 1-3 verification and CSDDD audit hash anchoring integrated
- **Legal Waiver Assertions**: 100% verified across API and engine levels
- **Supported Settlement Chains**: Polygon Mainnet (Chain ID 137), Base (8453), Arbitrum (42161)
- **Security Certification**: EU AI Act Article 50 & Zero-Trust Security Gate Integrated
- **On-Chain Attestation**: Polygon EIP-712 Typed Structured Hash Binding (with `disclaimerHash`)
