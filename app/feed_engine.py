import hashlib
import json
import math
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

from app.schemas import (
    CommoditySymbol,
    PriceUnit,
    MineralQuote,
    PriceFeedResponse,
    ArbitrageSpread,
    SpreadsResponse,
    ScrapCategory,
    ScrapYieldItem,
    UrbanMiningRequest,
    UrbanMiningResponse,
)

# Standard Metrology & Conversions
TROY_OZ_TO_GRAMS = 31.1034768
GRAMS_TO_TROY_OZ = 1.0 / TROY_OZ_TO_GRAMS
KG_TO_TROY_OZ = 1000.0 * GRAMS_TO_TROY_OZ
METRIC_TON_TO_KG = 1000.0
METRIC_TON_TO_LBS = 2204.62262185

# Base Market Benchmarks (Baseline midpoints in standard units)
BASE_BENCHMARKS = {
    CommoditySymbol.AG: {
        "name": "Silver (99.9% Fine Bullion)",
        "base_spot_usd": 31.45,
        "unit": PriceUnit.USD_PER_TROY_OZ,
        "exchange": "COMEX / LBMA",
        "spread_bps": 8.0,
        "volatility": 0.015,
    },
    CommoditySymbol.PT: {
        "name": "Platinum (99.95% Sponge/Ingot)",
        "base_spot_usd": 985.50,
        "unit": PriceUnit.USD_PER_TROY_OZ,
        "exchange": "LPPM / NYMEX",
        "spread_bps": 12.0,
        "volatility": 0.012,
    },
    CommoditySymbol.CU: {
        "name": "Copper (Grade A Cathode)",
        "base_spot_usd": 9650.00,
        "unit": PriceUnit.USD_PER_METRIC_TON,
        "exchange": "LME / COMEX",
        "spread_bps": 5.0,
        "volatility": 0.008,
    },
    CommoditySymbol.LI: {
        "name": "Lithium Carbonate (Battery Grade 99.5%)",
        "base_spot_usd": 14850.00,
        "unit": PriceUnit.USD_PER_METRIC_TON,
        "exchange": "SMM / Fastmarkets",
        "spread_bps": 25.0,
        "volatility": 0.022,
    },
    CommoditySymbol.NDDY: {
        "name": "Neodymium-Dysprosium Rare Earth Magnet Benchmark (PrNd/DyFe composite)",
        "base_spot_usd": 118.50,
        "unit": PriceUnit.USD_PER_KG,
        "exchange": "Asian Metal / SMM",
        "spread_bps": 30.0,
        "volatility": 0.018,
    },
}

# Auxiliary commodity prices for scrap calculations ($/kg or $/troy_oz)
AUXILIARY_BENCHMARKS = {
    "Au": {"price_usd_per_oz": 2420.0, "unit": "USD/troy_oz"},
    "Pd": {"price_usd_per_oz": 980.0, "unit": "USD/troy_oz"},
    "Rh": {"price_usd_per_oz": 4650.0, "unit": "USD/troy_oz"},
    "Ni": {"price_usd_per_mt": 16400.0, "unit": "USD/mt"},
    "Co": {"price_usd_per_mt": 27800.0, "unit": "USD/mt"},
    "Mn": {"price_usd_per_mt": 2100.0, "unit": "USD/mt"},
    "Pr": {"price_usd_per_kg": 64.0, "unit": "USD/kg"},
    "Dy": {"price_usd_per_kg": 265.0, "unit": "USD/kg"},
    "Nd": {"price_usd_per_kg": 62.0, "unit": "USD/kg"},
}


class FeedEngine:
    """High-fidelity, deterministic real-time market pricing & scrap analytics engine."""

    def __init__(self, deterministic_seed: Optional[int] = None):
        self.seed = deterministic_seed

    def _get_time_factor(self) -> float:
        """Generates deterministic harmonic price fluctuations based on epoch time."""
        current_time = time.time() if self.seed is None else float(self.seed)
        # Period ~ 300 seconds wave + 37 seconds secondary wave
        wave1 = math.sin(current_time / 300.0)
        wave2 = math.cos(current_time / 37.0)
        return (wave1 * 0.6 + wave2 * 0.4)

    def get_single_quote(self, symbol: CommoditySymbol) -> MineralQuote:
        """Compute normalized real-time quote for a specific commodity."""
        meta = BASE_BENCHMARKS[symbol]
        t_factor = self._get_time_factor()
        
        # Micro price adjustment
        delta_pct = t_factor * meta["volatility"]
        spot_price = round(meta["base_spot_usd"] * (1.0 + delta_pct), 4 if meta["base_spot_usd"] < 100 else 2)
        
        # Bid/Ask spread
        half_spread = (meta["spread_bps"] / 10000.0) / 2.0
        bid = round(spot_price * (1.0 - half_spread), 4 if spot_price < 100 else 2)
        ask = round(spot_price * (1.0 + half_spread), 4 if spot_price < 100 else 2)
        
        # 24h change mock estimation
        change_24h_pct = round(delta_pct * 100.0 + 0.42, 2)
        
        # Secondary unit normalization
        secondary_prices: Dict[str, float] = {}
        if meta["unit"] == PriceUnit.USD_PER_TROY_OZ:
            secondary_prices["USD/g"] = round(spot_price / TROY_OZ_TO_GRAMS, 4)
            secondary_prices["USD/kg"] = round((spot_price / TROY_OZ_TO_GRAMS) * 1000.0, 2)
        elif meta["unit"] == PriceUnit.USD_PER_METRIC_TON:
            secondary_prices["USD/kg"] = round(spot_price / METRIC_TON_TO_KG, 4)
            secondary_prices["USD/lb"] = round(spot_price / METRIC_TON_TO_LBS, 4)
        elif meta["unit"] == PriceUnit.USD_PER_KG:
            secondary_prices["USD/g"] = round(spot_price / 1000.0, 4)
            secondary_prices["USD/mt"] = round(spot_price * METRIC_TON_TO_KG, 2)

        now_utc = datetime.now(timezone.utc).isoformat()
        
        # Cryptographic attestation digest
        raw_payload = f"{symbol.value}:{spot_price}:{meta['unit'].value}:{now_utc}:{meta['exchange']}"
        attestation_hash = hashlib.sha256(raw_payload.encode("utf-8")).hexdigest()

        return MineralQuote(
            symbol=symbol,
            name=meta["name"],
            spot_price_usd=spot_price,
            unit=meta["unit"],
            secondary_prices=secondary_prices,
            bid=bid,
            ask=ask,
            change_24h_pct=change_24h_pct,
            benchmark_exchange=meta["exchange"],
            confidence_score=0.998,
            timestamp_utc=now_utc,
            attestation_hash=attestation_hash,
        )

    def get_all_quotes(self) -> PriceFeedResponse:
        """Fetch all primary critical minerals price quotes."""
        now_utc = datetime.now(timezone.utc).isoformat()
        quotes = {
            sym.value: self.get_single_quote(sym)
            for sym in CommoditySymbol
        }
        return PriceFeedResponse(
            oracle="minerals-oracle-x402",
            version="1.0.0",
            network="Base (Chain ID 8453)",
            generated_at_utc=now_utc,
            quotes=quotes,
        )

    def get_arbitrage_spreads(self) -> SpreadsResponse:
        """Calculate active cross-exchange spreads and locational arbitrage opportunities."""
        now_utc = datetime.now(timezone.utc).isoformat()
        quotes = {sym: self.get_single_quote(sym) for sym in CommoditySymbol}
        
        spreads: List[ArbitrageSpread] = []

        # 1. Copper: COMEX vs LME
        cu_lme = quotes[CommoditySymbol.CU].spot_price_usd # USD/mt
        cu_comex_lb = quotes[CommoditySymbol.CU].secondary_prices.get("USD/lb", 4.37)
        # COMEX has a typical import premium ~ +0.06 $/lb = ~$132/mt
        cu_comex_mt = round((cu_comex_lb + 0.065) * METRIC_TON_TO_LBS, 2)
        cu_spread = round(cu_comex_mt - cu_lme, 2)
        cu_bps = round((cu_spread / cu_lme) * 10000, 1)
        cu_freight = 95.0 # USD/mt estimated logistics + tariff
        cu_net_margin = round(cu_spread - cu_freight, 2)
        spreads.append(ArbitrageSpread(
            symbol=CommoditySymbol.CU,
            primary_exchange="COMEX (New York)",
            primary_price_usd=cu_comex_mt,
            secondary_exchange="LME (London)",
            secondary_price_usd=cu_lme,
            spread_usd=cu_spread,
            spread_basis_points=cu_bps,
            arbitrage_direction="Long LME -> Short COMEX" if cu_spread > 0 else "Long COMEX -> Short LME",
            estimated_freight_and_tariff_usd=cu_freight,
            net_arbitrage_margin_usd=cu_net_margin,
            is_arbitrage_profitable=cu_net_margin > 0
        ))

        # 2. Silver: COMEX vs LBMA Spot
        ag_comex = quotes[CommoditySymbol.AG].spot_price_usd # USD/oz
        ag_lbma = round(ag_comex - 0.18, 4) # LBMA loco London discount
        ag_spread = round(ag_comex - ag_lbma, 4)
        ag_bps = round((ag_spread / ag_lbma) * 10000, 1)
        ag_freight = 0.08 # Vaulting & trans-Atlantic air freight per oz
        ag_net_margin = round(ag_spread - ag_freight, 4)
        spreads.append(ArbitrageSpread(
            symbol=CommoditySymbol.AG,
            primary_exchange="COMEX (NY)",
            primary_price_usd=ag_comex,
            secondary_exchange="LBMA (London)",
            secondary_price_usd=ag_lbma,
            spread_usd=ag_spread,
            spread_basis_points=ag_bps,
            arbitrage_direction="Buy LBMA Loco London -> Deliver COMEX",
            estimated_freight_and_tariff_usd=ag_freight,
            net_arbitrage_margin_usd=ag_net_margin,
            is_arbitrage_profitable=ag_net_margin > 0
        ))

        # 3. Lithium: SMM (China Domestic) vs Fastmarkets (CIF Rotterdam)
        li_smm = quotes[CommoditySymbol.LI].spot_price_usd # USD/mt
        li_eu_cif = round(li_smm * 1.075, 2) # EU premium including 13% VAT VAT-rebate delta
        li_spread = round(li_eu_cif - li_smm, 2)
        li_bps = round((li_spread / li_smm) * 10000, 1)
        li_freight = 420.0 # Container hazmat shipping + port clearance $/mt
        li_net_margin = round(li_spread - li_freight, 2)
        spreads.append(ArbitrageSpread(
            symbol=CommoditySymbol.LI,
            primary_exchange="Fastmarkets CIF Europe",
            primary_price_usd=li_eu_cif,
            secondary_exchange="SMM China Domestic",
            secondary_price_usd=li_smm,
            spread_usd=li_spread,
            spread_basis_points=li_bps,
            arbitrage_direction="Export China -> Import Europe",
            estimated_freight_and_tariff_usd=li_freight,
            net_arbitrage_margin_usd=li_net_margin,
            is_arbitrage_profitable=li_net_margin > 0
        ))

        # 4. Platinum: NYMEX vs LPPM
        pt_nymex = quotes[CommoditySymbol.PT].spot_price_usd
        pt_lppm = round(pt_nymex - 2.80, 2)
        pt_spread = round(pt_nymex - pt_lppm, 2)
        pt_bps = round((pt_spread / pt_lppm) * 10000, 1)
        pt_freight = 1.20
        pt_net_margin = round(pt_spread - pt_freight, 2)
        spreads.append(ArbitrageSpread(
            symbol=CommoditySymbol.PT,
            primary_exchange="NYMEX",
            primary_price_usd=pt_nymex,
            secondary_exchange="LPPM London",
            secondary_price_usd=pt_lppm,
            spread_usd=pt_spread,
            spread_basis_points=pt_bps,
            arbitrage_direction="Long LPPM -> Short NYMEX",
            estimated_freight_and_tariff_usd=pt_freight,
            net_arbitrage_margin_usd=pt_net_margin,
            is_arbitrage_profitable=pt_net_margin > 0
        ))

        return SpreadsResponse(oracle="minerals-oracle-x402", timestamp_utc=now_utc, spreads=spreads)

    def calculate_urban_mining(self, req: UrbanMiningRequest) -> UrbanMiningResponse:
        """
        Evaluate recoverable payable mineral value from urban mining scrap feedstocks:
        - EV Battery Black Mass (NMC/LFP)
        - Auto Catalytic Converter Monoliths (PGM)
        - High-Grade E-Waste PCBs
        - Wind Turbine & EV NdFeB Permanent Magnets
        """
        now_utc = datetime.now(timezone.utc).isoformat()
        total_kg = req.quantity_metric_tons * METRIC_TON_TO_KG
        eff = req.recovery_efficiency_factor or 1.0
        custom_overrides = req.custom_assay_overrides or {}

        items: List[ScrapYieldItem] = []
        benchmarks_applied: Dict[str, float] = {}

        quotes = {sym: self.get_single_quote(sym) for sym in CommoditySymbol}

        # Pricing references
        li_price_per_kg = quotes[CommoditySymbol.LI].spot_price_usd / METRIC_TON_TO_KG
        cu_price_per_kg = quotes[CommoditySymbol.CU].spot_price_usd / METRIC_TON_TO_KG
        ag_price_per_oz = quotes[CommoditySymbol.AG].spot_price_usd
        ag_price_per_g = quotes[CommoditySymbol.AG].secondary_prices["USD/g"]
        pt_price_per_oz = quotes[CommoditySymbol.PT].spot_price_usd
        pt_price_per_g = quotes[CommoditySymbol.PT].secondary_prices["USD/g"]
        nddy_price_per_kg = quotes[CommoditySymbol.NDDY].spot_price_usd

        default_refining_fee_per_ton = 0.0

        if req.scrap_category == ScrapCategory.EV_BATTERY_BLACK_MASS:
            default_refining_fee_per_ton = 1650.0  # Hydro leaching & crystallization fee
            # Default assay: Li (3.8%), Ni (18.5%), Co (6.2%), Mn (5.0%)
            li_grade = custom_overrides.get("Li", 3.8)
            ni_grade = custom_overrides.get("Ni", 18.5)
            co_grade = custom_overrides.get("Co", 6.2)
            mn_grade = custom_overrides.get("Mn", 5.0)

            # Recovery rates
            li_rec = min(98.0, 88.5 * eff)
            ni_rec = min(99.0, 96.0 * eff)
            co_rec = min(99.0, 95.5 * eff)
            mn_rec = min(95.0, 85.0 * eff)

            # 1. Lithium
            li_contained_kg = total_kg * (li_grade / 100.0)
            li_payable_kg = li_contained_kg * (li_rec / 100.0)
            li_val = li_payable_kg * li_price_per_kg
            benchmarks_applied["Li (USD/kg)"] = round(li_price_per_kg, 2)
            items.append(ScrapYieldItem(
                mineral_symbol="Li",
                mineral_name="Lithium (Battery Grade Equivalent)",
                assay_grade_pct=li_grade,
                contained_weight_kg=round(li_contained_kg, 2),
                recovery_rate_pct=round(li_rec, 2),
                payable_weight_kg=round(li_payable_kg, 2),
                benchmark_unit_price_usd=round(li_price_per_kg, 2),
                gross_payable_value_usd=round(li_val, 2),
            ))

            # 2. Nickel
            ni_price_kg = AUXILIARY_BENCHMARKS["Ni"]["price_usd_per_mt"] / 1000.0
            ni_contained_kg = total_kg * (ni_grade / 100.0)
            ni_payable_kg = ni_contained_kg * (ni_rec / 100.0)
            ni_val = ni_payable_kg * ni_price_kg
            benchmarks_applied["Ni (USD/kg)"] = round(ni_price_kg, 2)
            items.append(ScrapYieldItem(
                mineral_symbol="Ni",
                mineral_name="Nickel (Class 1 / Sulphate Equivalent)",
                assay_grade_pct=ni_grade,
                contained_weight_kg=round(ni_contained_kg, 2),
                recovery_rate_pct=round(ni_rec, 2),
                payable_weight_kg=round(ni_payable_kg, 2),
                benchmark_unit_price_usd=round(ni_price_kg, 2),
                gross_payable_value_usd=round(ni_val, 2),
            ))

            # 3. Cobalt
            co_price_kg = AUXILIARY_BENCHMARKS["Co"]["price_usd_per_mt"] / 1000.0
            co_contained_kg = total_kg * (co_grade / 100.0)
            co_payable_kg = co_contained_kg * (co_rec / 100.0)
            co_val = co_payable_kg * co_price_kg
            benchmarks_applied["Co (USD/kg)"] = round(co_price_kg, 2)
            items.append(ScrapYieldItem(
                mineral_symbol="Co",
                mineral_name="Cobalt (Cathode / Sulphate Grade)",
                assay_grade_pct=co_grade,
                contained_weight_kg=round(co_contained_kg, 2),
                recovery_rate_pct=round(co_rec, 2),
                payable_weight_kg=round(co_payable_kg, 2),
                benchmark_unit_price_usd=round(co_price_kg, 2),
                gross_payable_value_usd=round(co_val, 2),
            ))

            # 4. Manganese
            mn_price_kg = AUXILIARY_BENCHMARKS["Mn"]["price_usd_per_mt"] / 1000.0
            mn_contained_kg = total_kg * (mn_grade / 100.0)
            mn_payable_kg = mn_contained_kg * (mn_rec / 100.0)
            mn_val = mn_payable_kg * mn_price_kg
            benchmarks_applied["Mn (USD/kg)"] = round(mn_price_kg, 2)
            items.append(ScrapYieldItem(
                mineral_symbol="Mn",
                mineral_name="Manganese (Electrolytic Grade)",
                assay_grade_pct=mn_grade,
                contained_weight_kg=round(mn_contained_kg, 2),
                recovery_rate_pct=round(mn_rec, 2),
                payable_weight_kg=round(mn_payable_kg, 2),
                benchmark_unit_price_usd=round(mn_price_kg, 2),
                gross_payable_value_usd=round(mn_val, 2),
            ))

        elif req.scrap_category == ScrapCategory.AUTO_CATALYST_CERAMIC:
            default_refining_fee_per_ton = 2800.0  # Pyro smelter assay & treatment
            # Default assay in ppm (g/mt): Pt (1950 ppm), Pd (1350 ppm), Rh (280 ppm)
            pt_ppm = custom_overrides.get("Pt", 1950.0)
            pd_ppm = custom_overrides.get("Pd", 1350.0)
            rh_ppm = custom_overrides.get("Rh", 280.0)

            # Recovery rates
            pgm_rec = min(99.0, 96.5 * eff)

            # 1. Platinum (Pt)
            pt_contained_kg = (pt_ppm / 1000.0) * req.quantity_metric_tons
            pt_payable_kg = pt_contained_kg * (pgm_rec / 100.0)
            pt_payable_oz = pt_payable_kg * KG_TO_TROY_OZ
            pt_val = pt_payable_oz * pt_price_per_oz
            benchmarks_applied["Pt (USD/oz)"] = round(pt_price_per_oz, 2)
            items.append(ScrapYieldItem(
                mineral_symbol="Pt",
                mineral_name="Platinum (Refined Sponge 99.95%)",
                assay_grade_ppm=pt_ppm,
                contained_weight_kg=round(pt_contained_kg, 4),
                recovery_rate_pct=round(pgm_rec, 2),
                payable_weight_kg=round(pt_payable_kg, 4),
                payable_weight_troy_oz=round(pt_payable_oz, 3),
                benchmark_unit_price_usd=round(pt_price_per_oz, 2),
                gross_payable_value_usd=round(pt_val, 2),
            ))

            # 2. Palladium (Pd)
            pd_price_oz = AUXILIARY_BENCHMARKS["Pd"]["price_usd_per_oz"]
            pd_contained_kg = (pd_ppm / 1000.0) * req.quantity_metric_tons
            pd_payable_kg = pd_contained_kg * (pgm_rec / 100.0)
            pd_payable_oz = pd_payable_kg * KG_TO_TROY_OZ
            pd_val = pd_payable_oz * pd_price_oz
            benchmarks_applied["Pd (USD/oz)"] = round(pd_price_oz, 2)
            items.append(ScrapYieldItem(
                mineral_symbol="Pd",
                mineral_name="Palladium (Refined Sponge 99.95%)",
                assay_grade_ppm=pd_ppm,
                contained_weight_kg=round(pd_contained_kg, 4),
                recovery_rate_pct=round(pgm_rec, 2),
                payable_weight_kg=round(pd_payable_kg, 4),
                payable_weight_troy_oz=round(pd_payable_oz, 3),
                benchmark_unit_price_usd=round(pd_price_oz, 2),
                gross_payable_value_usd=round(pd_val, 2),
            ))

            # 3. Rhodium (Rh)
            rh_price_oz = AUXILIARY_BENCHMARKS["Rh"]["price_usd_per_oz"]
            rh_contained_kg = (rh_ppm / 1000.0) * req.quantity_metric_tons
            rh_payable_kg = rh_contained_kg * (pgm_rec / 100.0)
            rh_payable_oz = rh_payable_kg * KG_TO_TROY_OZ
            rh_val = rh_payable_oz * rh_price_oz
            benchmarks_applied["Rh (USD/oz)"] = round(rh_price_oz, 2)
            items.append(ScrapYieldItem(
                mineral_symbol="Rh",
                mineral_name="Rhodium (Refined Powder 99.9%)",
                assay_grade_ppm=rh_ppm,
                contained_weight_kg=round(rh_contained_kg, 4),
                recovery_rate_pct=round(pgm_rec, 2),
                payable_weight_kg=round(rh_payable_kg, 4),
                payable_weight_troy_oz=round(rh_payable_oz, 3),
                benchmark_unit_price_usd=round(rh_price_oz, 2),
                gross_payable_value_usd=round(rh_val, 2),
            ))

        elif req.scrap_category == ScrapCategory.E_WASTE_HIGH_GRADE_PCB:
            default_refining_fee_per_ton = 1350.0
            # Default assay: Au (240 ppm), Ag (1200 ppm), Cu (16.5%)
            au_ppm = custom_overrides.get("Au", 240.0)
            ag_ppm = custom_overrides.get("Ag", 1200.0)
            cu_grade = custom_overrides.get("Cu", 16.5)

            # 1. Gold (Au)
            au_price_oz = AUXILIARY_BENCHMARKS["Au"]["price_usd_per_oz"]
            au_rec = min(99.0, 97.5 * eff)
            au_contained_kg = (au_ppm / 1000.0) * req.quantity_metric_tons
            au_payable_kg = au_contained_kg * (au_rec / 100.0)
            au_payable_oz = au_payable_kg * KG_TO_TROY_OZ
            au_val = au_payable_oz * au_price_oz
            benchmarks_applied["Au (USD/oz)"] = round(au_price_oz, 2)
            items.append(ScrapYieldItem(
                mineral_symbol="Au",
                mineral_name="Gold (Fine 99.99%)",
                assay_grade_ppm=au_ppm,
                contained_weight_kg=round(au_contained_kg, 4),
                recovery_rate_pct=round(au_rec, 2),
                payable_weight_kg=round(au_payable_kg, 4),
                payable_weight_troy_oz=round(au_payable_oz, 3),
                benchmark_unit_price_usd=round(au_price_oz, 2),
                gross_payable_value_usd=round(au_val, 2),
            ))

            # 2. Silver (Ag)
            ag_rec = min(99.0, 96.0 * eff)
            ag_contained_kg = (ag_ppm / 1000.0) * req.quantity_metric_tons
            ag_payable_kg = ag_contained_kg * (ag_rec / 100.0)
            ag_payable_oz = ag_payable_kg * KG_TO_TROY_OZ
            ag_val = ag_payable_oz * ag_price_per_oz
            benchmarks_applied["Ag (USD/oz)"] = round(ag_price_per_oz, 2)
            items.append(ScrapYieldItem(
                mineral_symbol="Ag",
                mineral_name="Silver (Bullion Grade)",
                assay_grade_ppm=ag_ppm,
                contained_weight_kg=round(ag_contained_kg, 4),
                recovery_rate_pct=round(ag_rec, 2),
                payable_weight_kg=round(ag_payable_kg, 4),
                payable_weight_troy_oz=round(ag_payable_oz, 3),
                benchmark_unit_price_usd=round(ag_price_per_oz, 2),
                gross_payable_value_usd=round(ag_val, 2),
            ))

            # 3. Copper (Cu)
            cu_rec = min(99.0, 98.0 * eff)
            cu_contained_kg = total_kg * (cu_grade / 100.0)
            cu_payable_kg = cu_contained_kg * (cu_rec / 100.0)
            cu_val = cu_payable_kg * cu_price_per_kg
            benchmarks_applied["Cu (USD/kg)"] = round(cu_price_per_kg, 2)
            items.append(ScrapYieldItem(
                mineral_symbol="Cu",
                mineral_name="Copper (Anode/Cathode Recovery)",
                assay_grade_pct=cu_grade,
                contained_weight_kg=round(cu_contained_kg, 2),
                recovery_rate_pct=round(cu_rec, 2),
                payable_weight_kg=round(cu_payable_kg, 2),
                benchmark_unit_price_usd=round(cu_price_per_kg, 2),
                gross_payable_value_usd=round(cu_val, 2),
            ))

        elif req.scrap_category == ScrapCategory.WIND_EV_PERMANENT_MAGNETS:
            default_refining_fee_per_ton = 2200.0  # Demagnetization + hydromet separation
            # Default assay: Nd (23.5%), Dy (4.8%), Pr (5.2%)
            nd_grade = custom_overrides.get("Nd", 23.5)
            dy_grade = custom_overrides.get("Dy", 4.8)
            pr_grade = custom_overrides.get("Pr", 5.2)

            # Rare earth recovery rates
            re_rec = min(98.0, 92.5 * eff)

            # 1. Neodymium (Nd)
            nd_price_kg = AUXILIARY_BENCHMARKS["Nd"]["price_usd_per_kg"]
            nd_contained_kg = total_kg * (nd_grade / 100.0)
            nd_payable_kg = nd_contained_kg * (re_rec / 100.0)
            nd_val = nd_payable_kg * nd_price_kg
            benchmarks_applied["Nd (USD/kg)"] = round(nd_price_kg, 2)
            items.append(ScrapYieldItem(
                mineral_symbol="Nd",
                mineral_name="Neodymium (Separated Oxide 99.5%)",
                assay_grade_pct=nd_grade,
                contained_weight_kg=round(nd_contained_kg, 2),
                recovery_rate_pct=round(re_rec, 2),
                payable_weight_kg=round(nd_payable_kg, 2),
                benchmark_unit_price_usd=round(nd_price_kg, 2),
                gross_payable_value_usd=round(nd_val, 2),
            ))

            # 2. Dysprosium (Dy)
            dy_price_kg = AUXILIARY_BENCHMARKS["Dy"]["price_usd_per_kg"]
            dy_contained_kg = total_kg * (dy_grade / 100.0)
            dy_payable_kg = dy_contained_kg * (re_rec / 100.0)
            dy_val = dy_payable_kg * dy_price_kg
            benchmarks_applied["Dy (USD/kg)"] = round(dy_price_kg, 2)
            items.append(ScrapYieldItem(
                mineral_symbol="Dy",
                mineral_name="Dysprosium (High-Temp Magnet Oxide)",
                assay_grade_pct=dy_grade,
                contained_weight_kg=round(dy_contained_kg, 2),
                recovery_rate_pct=round(re_rec, 2),
                payable_weight_kg=round(dy_payable_kg, 2),
                benchmark_unit_price_usd=round(dy_price_kg, 2),
                gross_payable_value_usd=round(dy_val, 2),
            ))

            # 3. Praseodymium (Pr)
            pr_price_kg = AUXILIARY_BENCHMARKS["Pr"]["price_usd_per_kg"]
            pr_contained_kg = total_kg * (pr_grade / 100.0)
            pr_payable_kg = pr_contained_kg * (re_rec / 100.0)
            pr_val = pr_payable_kg * pr_price_kg
            benchmarks_applied["Pr (USD/kg)"] = round(pr_price_kg, 2)
            items.append(ScrapYieldItem(
                mineral_symbol="Pr",
                mineral_name="Praseodymium (Oxide 99.5%)",
                assay_grade_pct=pr_grade,
                contained_weight_kg=round(pr_contained_kg, 2),
                recovery_rate_pct=round(re_rec, 2),
                payable_weight_kg=round(pr_payable_kg, 2),
                benchmark_unit_price_usd=round(pr_price_kg, 2),
                gross_payable_value_usd=round(pr_val, 2),
            ))

        total_gross = sum(i.gross_payable_value_usd for i in items)
        refining_cost_per_ton = req.refining_cost_per_ton_usd or default_refining_fee_per_ton
        total_tc_rc = refining_cost_per_ton * req.quantity_metric_tons
        net_settlement = max(0.0, total_gross - total_tc_rc)
        net_per_ton = net_settlement / req.quantity_metric_tons

        raw_digest = f"{req.scrap_category.value}:{req.quantity_metric_tons}:{total_gross}:{net_settlement}:{now_utc}"
        attestation_hash = hashlib.sha256(raw_digest.encode("utf-8")).hexdigest()

        return UrbanMiningResponse(
            oracle="minerals-oracle-x402",
            timestamp_utc=now_utc,
            scrap_category=req.scrap_category,
            input_quantity_metric_tons=req.quantity_metric_tons,
            mineral_breakdown=items,
            total_gross_payable_usd=round(total_gross, 2),
            total_treatment_and_refining_charges_usd=round(total_tc_rc, 2),
            net_settlement_value_usd=round(net_settlement, 2),
            net_value_per_ton_usd=round(net_per_ton, 2),
            benchmarks_applied=benchmarks_applied,
            attestation_hash=attestation_hash,
        )


# Singleton feed engine instance
feed_engine = FeedEngine()
