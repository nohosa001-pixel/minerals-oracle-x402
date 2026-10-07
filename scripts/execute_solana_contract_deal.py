"""
Execute Solana DynamicTradeEscrow Deal Transaction
Triggers deal initialization, Anchor instruction generation, and sub-second fee-split settlement.
"""

import os
import json
import asyncio
from datetime import datetime, timezone
from app.a2a_deal_engine import A2ATradeDealEngine
from app.schemas import TradeDealProposeRequest, TradeDealDualSignRequest, TradeDealSpec, MineralType, SourceCountry
from app.security_gate_client import security_gate_client

async def main():
    engine = A2ATradeDealEngine()
    deal_id = f"DEAL-SOL-DYN-CU-{int(datetime.now(timezone.utc).timestamp())}"
    
    seller = "411ksMz9RHYVtVMe6RUUErzZYtrU9zzvkgzswKbqx9qp"
    buyer = "774hK5wmk5pStvsh5DH46pYPYYD3ro7tMfz1ASxcbiTK"
    
    print("=================================================================")
    print(">>> 1. Creating Solana Dynamic Trade Deal Proposal <<<")
    print("=================================================================")
    
    spec = TradeDealSpec(
        deal_id=deal_id,
        commodity=MineralType.COPPER_CATHODE,
        volume_tons=50.0,
        unit_price_usd_per_ton=6610.0,
        total_deal_value_usd=330500.0,
        origin_country=SourceCountry.CHL,
        destination_country="KR",
        ebl_document_id=f"EBL-SOL-{deal_id}",
        buyer_agent_address=buyer,
        seller_agent_address=seller,
        created_at_utc="2026-10-07T12:00:00Z",
    )
    
    # Seller creates proposal
    seller_sig = "0x" + "a" * 130
    prop_req = TradeDealProposeRequest(spec=spec, seller_signature=seller_sig)
    att_prop = engine.propose_deal(prop_req)
    print(f"Deal Proposed: {deal_id} (Status: {att_prop.status})")
    
    # Buyer countersigns
    buyer_sig = "0x" + "c" * 130
    dual_req = TradeDealDualSignRequest(
        deal_id=deal_id,
        buyer_agent_address=buyer,
        buyer_signature=buyer_sig
    )
    att_dual = engine.dual_sign_deal(dual_req)
    print(f"Deal Dual-Signed: {deal_id} (Status: {att_dual.status})")
    print(f"Immutable Contract Hash: {att_dual.final_contract_hash}")
    
    print("\n=================================================================")
    print(">>> 2. Generating Solana Anchor Dynamic Escrow Instruction <<<")
    print("=================================================================")
    
    # Build Solana Anchor createDeal instruction
    anchor_ix = engine.build_solana_dynamic_escrow_instruction(
        deal_id=deal_id,
        collateral_deposit_usdc=33050.0,  # 10% collateral
        pyth_price_feed="EdVCdQsbCDnvokWiLTVfdc2b9YPLRBVT69LL7ahAo28c",  # Solana Pyth Cu Feed
        base_price_usd=6610.0,
        min_collateral_ratio_bps=11000
    )
    
    print(f"Program ID           : {anchor_ix['program_id']}")
    print(f"Instruction          : {anchor_ix['instruction_name']}")
    print(f"Discriminator        : {anchor_ix['discriminator_hex']}")
    print(f"Deal Value           : ${anchor_ix['total_deal_amount_usdc']:,} USDC")
    print(f"Collateral Deposit   : ${anchor_ix['collateral_deposit_usdc']:,} USDC")
    print(f"Total Required       : ${anchor_ix['total_required_deposit_usdc']:,} USDC")
    print(f"Solscan Explorer URL : {anchor_ix['solscan_program_url']}")
    print(f"Solscan IDL Tab      : {anchor_ix['solscan_idl_tab']}")
    
    print("\n=================================================================")
    print(">>> 3. Executing Sub-Second Direct Split Settlement on Solana <<<")
    print("=================================================================")
    
    settle_res = await security_gate_client.settle_solana_universal_escrow_async(
        deal_id=deal_id,
        buyer_agent_pubkey=buyer,
        seller_agent_pubkey=seller,
        gross_amount_usdc=spec.total_deal_value_usd,
        oracle_domain=4,
        oracle_id="minerals-oracle-solana-mainnet"
    )
    
    print(f"Settlement Status    : {settle_res.get('status')}")
    print(f"Settlement Rail      : {settle_res.get('settlement_rail')}")
    print(f"Transaction Signature: {settle_res.get('solana_tx_signature')}")
    print(f"Execution Latency    : {settle_res.get('latency_ms')} ms (Sub-Second 0.4s: {settle_res.get('sub_second_finality')})")
    print(f"Breakdown:")
    print(f"  - Seller Net (99.8%)     : ${settle_res['settlement_breakdown']['seller_agent_net_usdc']:,} USDC")
    print(f"  - Treasury Fee (0.1%)    : ${settle_res['settlement_breakdown']['minerals_oracle_fee_usdc']:,} USDC")
    print(f"  - Staking Pool (0.1%)    : ${settle_res['settlement_breakdown']['security_gate_staking_fee_usdc']:,} USDC")
    
    print("\n=================================================================")
    print(">>> [SUCCESS] Solana Dynamic Trade Escrow Lifecycle Completed <<<")
    print("=================================================================")

if __name__ == "__main__":
    asyncio.run(main())
