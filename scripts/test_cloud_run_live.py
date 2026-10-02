import httpx

client = httpx.Client(timeout=10.0)
base = "https://minerals-oracle-x402-212942243360.asia-northeast3.run.app"

r_health = client.get(f"{base}/health")
print("1. Live Cloud Run /health:", r_health.status_code, r_health.json())

r_solana = client.get(f"{base}/api/v1/solana/programs")
print("2. Live Cloud Run /api/v1/solana/programs:", r_solana.status_code, r_solana.json())

r_metrics = client.get(f"{base}/metrics")
print("3. Live Cloud Run /metrics contains 1.3.0:", 'oracle_system_version{version="1.3.0"}' in r_metrics.text)
