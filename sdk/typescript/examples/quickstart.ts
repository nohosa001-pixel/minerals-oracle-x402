/**
 * Minerals Oracle TypeScript SDK - Quickstart Example
 * Works both against local development server or live production Cloud Run node
 */

import { MineralsOracleClient } from '../src';

async function main() {
  // Use local server if running, otherwise live Cloud Run node
  const endpoint = process.env.ORACLE_URL || 'http://127.0.0.1:8000';
  console.log(`Connecting to Minerals Oracle at: ${endpoint}`);

  const client = new MineralsOracleClient({
    baseUrl: endpoint,
    vaultKey: process.env.ORACLE_VAULT_KEY || 'vault_key_demo_agent_sandbox_2026',
    devBypass: true
  });

  console.log('\n--- 1. Querying Live Health Status ---');
  const health = await client.getHealth();
  console.log('✓ Health:', health.status, '| Traps Defended:', health.traps_defended);

  console.log('\n--- 2. Auditing Sangdong Tungsten (US NDAA Sec 848) ---');
  try {
    const tungsten = await client.verifyTungsten({
      batch_id: 'W-APT-2026-T01',
      tenement_id: 'SANGDONG',
      latitude: 37.150,
      longitude: 128.833,
      apt_wo3_grade_pct: 88.5,
      dodd_frank_conflict_free: true,
      ndaa_defense_procurement_eligible: true
    });
    console.log('✓ Tungsten Verdict:', tungsten.audit_verdict?.status);
    console.log('✓ NDAA Eligible:', tungsten.audit_verdict?.ndaa_defense_eligible);
    console.log('✓ Proof Hash:', tungsten.proof_hash);
  } catch (err: any) {
    console.log('Notice:', err.message);
  }

  console.log('\n--- 3. Auditing Sarfartoq Rare Earths (China MOFCOM D-28) ---');
  try {
    const ree = await client.verifyRareEarths({
      batch_id: 'REE-NDPR-2026-MAG01',
      tenement_id: 'SARFARTOQ',
      latitude: 66.500,
      longitude: -51.250,
      ndpr_oxide_purity_pct: 99.55,
      declared_china_origin_ratio: 0.0005
    });
    console.log('✓ Rare Earths Verdict:', ree.audit_verdict?.status);
    console.log('✓ MOFCOM D-28 Eligible:', ree.audit_verdict?.mofcom_rule_d35_eligible);
  } catch (err: any) {
    console.log('Notice:', err.message);
  }

  console.log('\n--- 4. M2M Trade: Bilateral Deal Proposal & Dual-Signature ---');
  const dealId = `DEAL-SDK-${Date.now().toString().slice(-6)}`;
  try {
    const deal = await client.proposeTradeDeal({
      deal_id: dealId,
      commodity_type: 'COPPER_CATHODE',
      quantity_metric_tons: 500.0,
      unit_price_usd: 9650.0,
      buyer_agent_address: '0x2222222222222222222222222222222222222222',
      seller_agent_address: '0x1111111111111111111111111111111111111111',
      seller_signature: '0x' + 'a'.repeat(130),
      delivery_incoterm: 'CIF_ROTTERDAM'
    });
    console.log('✓ Deal Proposed:', deal.deal_id, '| State:', deal.status || deal.deal_state);

    const dualSigned = await client.dualSignTradeDeal({
      deal_id: deal.deal_id,
      buyer_signature: '0x' + 'b'.repeat(130),
      buyer_agent_address: '0x2222222222222222222222222222222222222222'
    });
    console.log('✓ Dual-Signed & Oracle Sealed:', dualSigned.status || dualSigned.deal_state);

    console.log('\n--- 5. Generating On-Chain Multi-Chain Escrow Calldata ---');
    const escrow = await client.getEscrowCalldata(dualSigned.deal_id, 'polygon');
    console.log('✓ Target Escrow Contract:', escrow.escrow_contract_address);
    console.log('✓ Target Chain ID:', escrow.chain_id);
    console.log('✓ Calldata Bytecode Length:', escrow.calldata.length, 'characters');
    console.log('✓ Function Selector:', escrow.function_signature);
    console.log('✓ Machine Next Action:', escrow.next_action);
  } catch (err: any) {
    console.log('Trade Notice:', err.message);
  }
}

main().catch(console.error);
