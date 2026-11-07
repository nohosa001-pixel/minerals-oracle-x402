"""
Generate all 6 static EU Battery Regulation (2023/1542) & US IRA Section 30D
compliant Battery Passport JSON files into app/static.
"""

import json
from pathlib import Path
from app.battery_chemistry_catalog import CHEMISTRY_CATALOG, generate_battery_passport_payload

STATIC_DIR = Path("app/static")
STATIC_DIR.mkdir(parents=True, exist_ok=True)

fixed_timestamp = "2026-11-07T00:00:00.000000+00:00"

for code in CHEMISTRY_CATALOG.keys():
    payload = generate_battery_passport_payload(
        chemistry_code=code,
        timestamp_iso=fixed_timestamp
    )
    filename = f"EU_BATTERY_PASSPORT_EIP712_{code}.json"
    file_path = STATIC_DIR / filename
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    print(f"Generated: {file_path} ({len(json.dumps(payload))} bytes)")

# Also update the canonical backward-compatible sample (NCM811)
sample_path = STATIC_DIR / "EU_BATTERY_PASSPORT_EIP712_SAMPLE.json"
sample_payload = generate_battery_passport_payload(
    chemistry_code="NCM811",
    custom_pack_id="BATT-NCM811-2026-PACK01",
    custom_kwh=84.0,
    timestamp_iso=fixed_timestamp
)
with open(sample_path, "w", encoding="utf-8") as f:
    json.dump(sample_payload, f, indent=2)
print(f"Updated default sample: {sample_path}")

