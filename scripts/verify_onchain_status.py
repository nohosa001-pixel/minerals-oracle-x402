import json
from web3 import Web3

def main():
    with open('contracts/deployed_multichain.json', 'r', encoding='utf-8') as f:
        registry = json.load(f)

    abi = [
        {'inputs': [], 'name': 'owner', 'outputs': [{'internalType': 'address', 'name': '', 'type': 'address'}], 'stateMutability': 'view', 'type': 'function'},
        {'inputs': [], 'name': 'trustedOracleSigner', 'outputs': [{'internalType': 'address', 'name': '', 'type': 'address'}], 'stateMutability': 'view', 'type': 'function'},
        {'inputs': [], 'name': 'pythOracle', 'outputs': [{'internalType': 'contract IPyth', 'name': '', 'type': 'address'}], 'stateMutability': 'view', 'type': 'function'},
        {'inputs': [], 'name': 'usdcToken', 'outputs': [{'internalType': 'contract IERC20', 'name': '', 'type': 'address'}], 'stateMutability': 'view', 'type': 'function'},
        {'inputs': [], 'name': 'paused', 'outputs': [{'internalType': 'bool', 'name': '', 'type': 'bool'}], 'stateMutability': 'view', 'type': 'function'}
    ]

    rpcs = {
        'base': 'https://mainnet.base.org',
        'arbitrum': 'https://arb1.arbitrum.io/rpc',
        'polygon': 'https://polygon-bor-rpc.publicnode.com'
    }

    results = {}

    for chain_key in ['base', 'arbitrum', 'polygon']:
        net = registry['networks'][chain_key]
        rpc = rpcs[chain_key]
        w3 = Web3(Web3.HTTPProvider(rpc))
        chain_name = net.get('display_name', chain_key)
        chain_id = net.get('chainId')
        
        print(f"==================================================")
        print(f"Chain: {chain_name} (ChainID: {chain_id})")
        print(f"RPC Connected: {w3.is_connected()} | Current Block: {w3.eth.block_number}")
        
        dte = net['contracts']['DynamicTradeEscrow']
        contract_addr = Web3.to_checksum_address(dte['address'])
        raw_tx = dte['creation_tx']
        tx_hash = '0x' + raw_tx.replace('0x', '')
        
        # 1. Receipt verification
        receipt = w3.eth.get_transaction_receipt(tx_hash)
        is_success = (receipt.status == 1)
        gas_used = receipt.gasUsed
        blk_num = receipt.blockNumber
        created_addr = receipt.contractAddress
        
        print(f"Creation Tx Hash: {tx_hash}")
        print(f"Tx Status       : {'SUCCESS (1)' if is_success else 'FAILED (0)'}")
        print(f"Deployed Block  : #{blk_num}")
        print(f"Gas Used        : {gas_used:,}")
        print(f"Created Address : {created_addr}")
        
        # 2. Bytecode verification
        code = w3.eth.get_code(contract_addr)
        print(f"Bytecode Size   : {len(code)} bytes")
        
        # 3. Read contract state variables
        contract = w3.eth.contract(address=contract_addr, abi=abi)
        owner_val = contract.functions.owner().call()
        oracle_val = contract.functions.trustedOracleSigner().call()
        pyth_val = contract.functions.pythOracle().call()
        usdc_val = contract.functions.usdcToken().call()
        paused_val = contract.functions.paused().call()
        
        print(f"--- Contract State On-Chain ---")
        print(f"owner()              : {owner_val}")
        print(f"trustedOracleSigner(): {oracle_val}")
        print(f"pythOracle()         : {pyth_val}")
        print(f"usdcToken()          : {usdc_val}")
        print(f"paused()             : {paused_val}")
        print(f"Explorer URL         : {dte.get('explorer_link')}")
        print()
        
        results[chain_key] = {
            'success': is_success,
            'contract_address': contract_addr,
            'matches_receipt': (created_addr.lower() == contract_addr.lower()),
            'code_size': len(code),
            'owner': owner_val,
            'usdcToken': usdc_val
        }

    all_ok = all(r['success'] and r['matches_receipt'] and r['code_size'] > 1000 for r in results.values())
    print(f"OVERALL DEPLOYMENT VERIFICATION: {'PASSED (ALL CHAINS ACTIVE)' if all_ok else 'FAILED'}")

if __name__ == '__main__':
    main()
