"""
Test automated execution of A2A Global Trade & Logistics Simulator.
"""

from scripts.a2a_global_trade_simulator import run_trade_simulation


def test_global_trade_simulation_run():
    result = run_trade_simulation()
    assert result["status"] == "SUCCESS"
    assert result["corridor_id"] == "CORR_CHL_USA_LI"
    assert result["hs_code"] == "2825.20.00"
    assert result["fta_duty_pct"] == 0.0
    assert result["ebl_valid"] is True
    assert result["transit_days"] > 0
    assert result["landed_cost_usd_per_mt"] > 0
