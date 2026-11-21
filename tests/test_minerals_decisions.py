import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.decisions_verifier import MineralsDecisionsVerifier


def test_minerals_decisions_fallback():
    verifier = MineralsDecisionsVerifier(api_key="")
    verifier.api_key = None
    res = verifier.fast_verify(document_text="Sample RMAP smelter cert")
    assert res["decisions_api_active"] is False
    assert res["passport_eligible"] is False


def test_minerals_decisions_mock_verify():
    verifier = MineralsDecisionsVerifier(api_key="dummy-key")
    mock_client = MagicMock()
    mock_ans = {
        "is_rmap_conformant": MagicMock(noul=0.97),
        "is_conflict_free": MagicMock(noul=0.99),
        "has_carbon_footprint": MagicMock(noul=0.92),
        "chemistry_profile": MagicMock(choice="NCM811"),
        "esg_compliance_score": MagicMock(score=1.95),
    }
    mock_client.decisions.create.return_value = MagicMock(answers=mock_ans)
    verifier._client = mock_client

    res = verifier.fast_verify(document_text="NCM811 cathode precursor RMAP verified carbon 4.2 kgCO2e/kg.")
    assert res["decisions_api_active"] is True
    assert res["passport_eligible"] is True
    assert res["chemistry_profile"] == "NCM811"
    assert res["esg_compliance_score"] == 1.95
    assert res["output_tokens_used"] == 0
