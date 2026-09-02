from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_ops_telemetry_endpoint():
    response = client.get("/api/v1/ops/telemetry")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["service_name"] == "minerals-oracle-x402"
    assert "finance" in data
    assert "accounting" in data
    assert "compliance_and_sla" in data
    assert "total_capital_usd" in data["finance"]
    assert "stock_account" in data["finance"]
    assert "futures_account" in data["finance"]

def test_ops_journals_endpoint():
    response = client.get("/api/v1/ops/journals?limit=10")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "trades" in data
    assert "cashouts" in data
