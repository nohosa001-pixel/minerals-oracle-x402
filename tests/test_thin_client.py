import json
from unittest.mock import MagicMock, patch
import mcp_server


def test_initialize_handshake():
    resp = mcp_server.handle_jsonrpc({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
    assert resp["result"]["serverInfo"]["name"] == "minerals-oracle-x402"
    assert resp["result"]["serverInfo"]["version"] == "2.0.0"


def test_tools_list_proxies_remote():
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"tools": [{"name": "verify_mineral_lot_compliance"}]}
    with patch("mcp_server.httpx.get", return_value=mock_resp) as mock_get:
        resp = mcp_server.handle_jsonrpc({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
        assert resp["result"]["tools"][0]["name"] == "verify_mineral_lot_compliance"
        mock_get.assert_called_once()


def test_tools_call_handles_402_paywall():
    mock_resp = MagicMock()
    mock_resp.status_code = 402
    mock_resp.json.return_value = {"error": "Payment Required", "code": 402}
    with patch("mcp_server.httpx.post", return_value=mock_resp):
        resp = mcp_server.handle_jsonrpc({
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "verify_mineral_lot_compliance", "arguments": {}},
        })
        assert resp["result"]["isError"] is True
        payload = json.loads(resp["result"]["content"][0]["text"])
        assert payload["http_status"] == 402


def test_zero_server_code_present():
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent
    assert not (root / "app").exists()
    assert not (root / "contracts").exists()
