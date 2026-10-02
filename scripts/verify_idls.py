import json
from pathlib import Path

p = Path("contracts/verification/solana")
idls = [
    "universal_escrow_core.idl.json",
    "agent_payment_vault.idl.json",
    "minerals_oracle_consumer.idl.json",
    "solscan_metadata.json"
]

print("=== Auditing IDL & Metadata JSON Files ===")
for f in idls:
    fp = p / f
    with open(fp, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    if f.endswith(".idl.json"):
        name = data.get("name")
        ver = data.get("version")
        ixs = len(data.get("instructions", []))
        accs = len(data.get("accounts", []))
        errs = len(data.get("errors", []))
        print(f"[PASS] {f}: name='{name}', version='{ver}', instructions={ixs}, accounts={accs}, errors={errs}")
    else:
        proj = data.get("project_name")
        progs = len(data.get("programs", []))
        print(f"[PASS] {f}: project='{proj}', registered_programs={progs}")
