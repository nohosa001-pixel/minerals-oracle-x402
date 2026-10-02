import httpx
import json
import sys

programs = {
    "UniversalEscrowCore": "AGR3W3R9pKxnuZGYrpaggfkbMKVrjoniLaGvi1voBFSC",
    "AgentPaymentVault": "7oZ16YaazQzN6z5uA1nAZWD9oGUDXyvHwXGJLFYyWi3y",
    "MineralsOracleConsumer": "21ZR1QCyAbNrRLs1iWEkdbNsfCFdJcy6ip9R2JxDbkTL",
}

accounts = {
    "Treasury": "411ksMz9RHYVtVMe6RUUErzZYtrU9zzvkgzswKbqx9qp",
    "SecurityGateStakingPool": "774hK5wmk5pStvsh5DH46pYPYYD3ro7tMfz1ASxcbiTK",
    "USDC_Mint": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
}

rpc_urls = [
    "https://api.mainnet-beta.solana.com",
    "https://rpc.ankr.com/solana",
]

def check():
    client = httpx.Client(timeout=12.0)
    print("=================================================================")
    print(">>> 1. Checking Solana Mainnet-Beta On-Chain Program Accounts <<<")
    print("=================================================================")
    
    for name, pid in programs.items():
        found = False
        for rpc in rpc_urls:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getAccountInfo",
                "params": [pid, {"encoding": "jsonParsed"}]
            }
            try:
                res = client.post(rpc, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    val = data.get("result", {}).get("value")
                    if val is not None:
                        is_exec = val.get("executable")
                        owner = val.get("owner")
                        lamports = val.get("lamports")
                        rent_epoch = val.get("rentEpoch")
                        print(f"[{'PASS' if is_exec else 'NOTE'}] {name}")
                        print(f"       Pubkey:     {pid}")
                        print(f"       Executable: {is_exec}")
                        print(f"       Owner:      {owner}")
                        print(f"       Balance:    {lamports / 1e9:.4f} SOL")
                        print(f"       RPC Node:   {rpc}")
                        found = True
                        break
                    else:
                        print(f"[UNALLOCATED/OFFCHAIN] {name} ({pid}) returned null account data on {rpc}")
                        found = True
                        break
            except Exception as e:
                # try next rpc
                continue
        if not found:
            print(f"[FAIL] Could not reach RPC for {name} ({pid})")

    print("\n=================================================================")
    print(">>> 2. Checking Solana Associated Vault / Mint / Treasury <<<")
    print("=================================================================")
    for name, addr in accounts.items():
        for rpc in rpc_urls:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getAccountInfo",
                "params": [addr, {"encoding": "jsonParsed"}]
            }
            try:
                res = client.post(rpc, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    val = data.get("result", {}).get("value")
                    if val is not None:
                        owner = val.get("owner")
                        lamports = val.get("lamports")
                        print(f"[PASS] {name} ({addr}):")
                        print(f"       Owner:   {owner}")
                        print(f"       Balance: {lamports / 1e9:.4f} SOL")
                        break
                    else:
                        print(f"[NOTE] {name} ({addr}): Account data is null (unfunded/virtual PDA)")
                        break
            except Exception:
                continue

if __name__ == "__main__":
    check()
