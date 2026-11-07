"""
Unit tests for Battery Cell Chemistry Catalog & Composite Pipeline.
"""

from app.battery_chemistry_catalog import (
    CHEMISTRY_CATALOG,
    get_chemistry_spec,
    list_chemistry_catalog,
    generate_battery_passport_payload,
    normalize_chemistry_code,
)
from app.composite_battery_pipeline import CompositeBatteryPipeline
from app.schemas import (
    CompositeBatteryVerifyRequest,
    LithiumOriginVerifyRequest,
    NickelOriginVerifyRequest,
    CobaltOriginVerifyRequest,
)


def test_battery_chemistries_catalog_lineup():
    supported = list_chemistry_catalog()
    assert len(supported) == 6
    codes = {spec["code"] for spec in supported}
    assert codes == {"NCM811", "NCM9", "NCA", "NCMA", "LFP", "SOLID_STATE"}


def test_battery_passport_payload_generation():
    for code in ["NCM811", "NCM9", "NCA", "NCMA", "LFP", "SOLID_STATE"]:
        payload = generate_battery_passport_payload(code)
        assert payload["passport_data"]["cell_chemistry"] == code
        assert payload["technical_specifications"]["chemistry_code"] == code
        assert payload["passport_data"]["composite_verdict"]["eu_battery_passport_approved"] is True
        assert payload["passport_data"]["composite_verdict"]["ira_30d_tax_credit_eligible"] is True
        assert payload["_cryptographic_provenance"]["attestation_status"] == "APPROVED_COMPLIANT_ZERO_FEOC"


def test_composite_battery_pipeline_lfp_evaluation():
    pipeline = CompositeBatteryPipeline()
    req_lfp = CompositeBatteryVerifyRequest(
        battery_pack_id="BATT-LFP-TEST",
        cell_chemistry="LFP",
        pack_capacity_kwh=60.0,
        lithium_lot=LithiumOriginVerifyRequest(
            trace_id="LITH-01",
            product="Lithium Hydroxide Monohydrate",
            mine_name="Greenbushes",
            mine_country="AU",
            coordinates=[-33.864, 116.006],
            minedex_tenement_id="M01/03",
            spodumene_tonnage_extracted=7500.0,
            spodumene_grade_pct=6.0,
            refinery_facility="Kwinana",
            refinery_country="AU",
            refined_output_tonnage=1000.0,
            refinery_feoc_equity_pct=0.0
        ),
        nickel_lot=NickelOriginVerifyRequest(
            trace_id="NIC-01",
            product="Nickel MHP",
            concession_name="PT Morowali",
            coordinates=[-2.81, 122.15],
            simbara_ntpn="NTPN-884219482109",
            dhe_forex_deposit_ref="DHE-BI-992144-USD",
            limonite_ore_input_tons=9402.0,
            ore_grade_ni_pct=1.35,
            hpal_refinery_name="QMB Clean HPAL",
            mhp_output_tons=300.0,
            mhp_grade_ni_pct=38.5,
            captive_coal_power=False,
            feoc_equity_pct=0.0
        ),
        cobalt_lot=CobaltOriginVerifyRequest(
            trace_id="COB-01",
            product="Crude Cobalt Hydroxide",
            concession_name="KCC",
            province="Lualaba",
            coordinates=[-10.72, 25.47],
            mine_type="LSM",
            ceec_seal_id="CEEC-KAT-2026-992144",
            asm_comingled=False,
            zero_child_labor_audit_ref="ILO-AUDIT-01",
            heterogenite_ore_input_tons=2353.0,
            ore_grade_co_pct=1.50,
            refinery_name="Luilu",
            refinery_country="COD",
            rmi_rmap_smelter_id="CID002847",
            cobalt_hydroxide_output_tons=100.0,
            hydroxide_grade_co_pct=30.0,
            feoc_equity_pct=0.0
        )
    )
    res = pipeline.evaluate_battery_pack(req_lfp)
    assert res.composite_verdict.eu_battery_passport_approved is True
    assert res.composite_verdict.blended_carbon_footprint_kg_per_kwh == 41.0
