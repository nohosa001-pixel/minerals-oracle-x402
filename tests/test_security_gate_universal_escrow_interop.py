"""
Integration Tests for Minerals Oracle & Security Gate x402 Universal Escrow Interoperability.
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.security_gate_client import security_gate_client

client = TestClient(app)


def test_request_minerals_truth_attestation_payload():
    """Verify security_gate_client requests valid minerals truth attestation."""
    fake_response = {
        "domain": "CONFLICT_MINERALS",
        "domain_id": 4,
        "job_id": "job_minerals_interop_001",
        "is_valid": True,
        "child_labor_free": True,
        "signature": {
            "r": "0x1111",
            "s": "0x2222",
            "v": 27,
            "full_signature": "0x" + "bb" * 65
        }
    }

    with patch.object(security_gate_client._client, "post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = fake_response
        mock_post.return_value = mock_resp

        result = security_gate_client.request_minerals_truth_attestation(
            job_id="job_minerals_interop_001",
            mineral_type="cobalt",
            smelter_id="CID002991",
            smelter_audit_status="CONFORMANT",
            mine_country_code="CD",
            chain_of_custody_verified=True,
            child_labor_free=True
        )

        assert result["domain"] == "CONFLICT_MINERALS"
        assert result["is_valid"] is True
        assert mock_post.called
        call_args = mock_post.call_args
        assert "/api/v1/truth/minerals" in call_args[0][0]
        assert call_args[1]["json"]["mineral_type"] == "cobalt"


def test_settle_minerals_universal_escrow_payload():
    """Verify security_gate_client sends proper Direct Split disbursement for minerals."""
    fake_settle_response = {
        "status": "SETTLED",
        "job_id": "job_minerals_interop_001",
        "domain": 4,
        "total_disbursed_usdc": 35000.0
    }

    with patch.object(security_gate_client._client, "post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = fake_settle_response
        mock_post.return_value = mock_resp

        result = security_gate_client.settle_minerals_universal_escrow(
            job_id="job_minerals_interop_001",
            recipients=[{"recipient": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8", "amount": 35000.0}],
            attestation={"jobId": "job_minerals_interop_001", "isValid": True}
        )

        assert result["status"] == "SETTLED"
        assert result["total_disbursed_usdc"] == 35000.0
        assert mock_post.called
        call_args = mock_post.call_args
        assert "/api/v1/escrow/universal/settle" in call_args[0][0]
        assert call_args[1]["json"]["domain"] == 4


def test_api_settle_minerals_universal_escrow_endpoint():
    """Integration Test for POST /api/v1/escrow/universal/settle-minerals."""
    fake_attestation = {
        "domain": "CONFLICT_MINERALS",
        "domain_id": 4,
        "is_valid": True,
        "signature": {"full_signature": "0x999"}
    }
    fake_settlement = {
        "status": "SETTLED",
        "total_disbursed_usdc": 75000.0
    }

    with patch.object(security_gate_client, "request_minerals_truth_attestation", return_value=fake_attestation), \
         patch.object(security_gate_client, "settle_minerals_universal_escrow", return_value=fake_settlement):

        payload = {
            "job_id": "job_live_minerals_lithium_44",
            "mineral_type": "lithium",
            "smelter_id": "CID001928",
            "smelter_audit_status": "CONFORMANT",
            "mine_country_code": "AU",
            "chain_of_custody_verified": True,
            "child_labor_free": True,
            "conflict_region": False,
            "enhanced_due_diligence": True,
            "recipients": [{"recipient": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8", "amount": 75000.0}]
        }
        resp = client.post("/api/v1/escrow/universal/settle-minerals", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "SUCCESS"
        assert data["settlement"]["status"] == "SETTLED"
        assert data["settlement"]["total_disbursed_usdc"] == 75000.0
