# -*- coding: utf-8 -*-
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.eudr_client import eudr_client
from app.modules.copernicus_eudr_bridge import CopernicusEUDRBridge

sites = [
    ("Chile Salar de Atacama (Lithium Brine)", -23.86, -69.13, "CHL", "LITHIUM_HYDROXIDE"),
    ("Western Australia Greenbushes (Spodumene)", -33.86, 116.06, "AUS", "LITHIUM_CONCENTRATE"),
    ("Indonesia Morowali IMIP (Nickel HPAL)", -2.55, 121.35, "IDN", "NICKEL_MHP"),
    ("DRC Katanga Basin (Cobalt/Copper)", -10.72, 25.47, "COD", "COBALT_HYDROXIDE"),
]

print("=" * 80)
print("  MINERALS ORACLE X402: LIVE ESA COPERNICUS SENTINEL & EUDR SATELLITE QUERY")
print("=" * 80)

for name, lat, lon, country, comm in sites:
    result = eudr_client.verify_mine_site_compliance(
        latitude=lat,
        longitude=lon,
        country_code=country,
        area_hectares=15.0,
        concession_id=f"MINE-{country}-001"
    )
    print(f"\n[Satellite Observation] >>> {name}")
    print(f"  * Status: {'COMPLIANT' if result['is_compliant'] else 'NON-COMPLIANT'}")
    print(f"  * Audit Source: {result['audit_source']}")
    print(f"  * Hansen GFC Granule Tile: {result.get('hansen_gfc_tile')}")
    print(f"  * Forest Canopy Stability: {result.get('canopy_stability')}")
    print(f"  * Sentinel-2 NDMI Moisture Index: {result.get('ndmi_moisture_index')}")
    print(f"  * Copernicus Evidence Hash: {result['satellite_evidence_hash']}")
    print(f"  * Official TRACES-NT Reference: {result['traces_nt_dds_reference']}")
    if "ndvi_time_series" in result and isinstance(result["ndvi_time_series"], dict):
        years = list(result["ndvi_time_series"].keys())[:5]
        print(f"  * Multi-Year NDVI Timeline: {years}")
