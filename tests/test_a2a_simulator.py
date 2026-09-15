"""
Test automated A2A Simulator execution.
"""

from scripts.a2a_agent_simulator import run_simulation


def test_a2a_simulation_run():
    result = run_simulation()
    assert result["status"] == "SUCCESS"
    assert result["offer_a_verdict"] == "QUALIFIED"
    assert result["offer_b_verdict"] == "DISQUALIFIED"
    assert result["queries_executed"] >= 1
