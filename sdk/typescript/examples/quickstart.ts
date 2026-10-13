/**
 * Minerals Oracle TypeScript SDK - 3-Line Quickstart Example
 */

import { MineralsOracleClient } from '../src';

async function main() {
  // 1. Initialize client (defaults to production Cloud Run endpoint)
  const client = new MineralsOracleClient();

  console.log('--- 1. Querying Health Status ---');
  const health = await client.getHealth();
  console.log('Health:', health.status, 'Traps Defended:', health.traps_defended);

  console.log('\n--- 2. Auditing Sangdong Tungsten (US NDAA Sec 848) ---');
  const tungsten = await client.verifyTungsten({
    batch_id: 'W-APT-2026-T01',
    tenement_id: 'SANGDONG',
    latitude: 37.150,
    longitude: 128.833,
    apt_wo3_grade_pct: 88.5,
    dodd_frank_conflict_free: true,
    ndaa_defense_procurement_eligible: true
  });
  console.log('Tungsten Verdict:', tungsten.audit_verdict?.status);
  console.log('NDAA Eligible:', tungsten.audit_verdict?.ndaa_defense_eligible);
  console.log('Proof Hash:', tungsten.proof_hash);

  console.log('\n--- 3. Auditing Sarfartoq Rare Earths (China MOFCOM D-28) ---');
  const ree = await client.verifyRareEarths({
    batch_id: 'REE-NDPR-2026-MAG01',
    tenement_id: 'SARFARTOQ',
    latitude: 66.500,
    longitude: -51.250,
    ndpr_oxide_purity_pct: 99.55,
    declared_china_origin_ratio: 0.0005
  });
  console.log('Rare Earths Verdict:', ree.audit_verdict?.status);
  console.log('MOFCOM D-28 Eligible:', ree.audit_verdict?.mofcom_rule_d35_eligible);

  console.log('\n--- 4. Auditing NioCorp Elk Creek Niobium & Scandium ---');
  const nb = await client.verifyNiobiumScandium({
    batch_id: 'NB-SC-2026-DEF01',
    tenement_id: 'ELK_CREEK',
    latitude: 40.288,
    longitude: -96.184,
    commodity_type: 'FERRONIOBIUM',
    fe_nb_grade_pct: 66.50,
    sc2o3_purity_pct: 99.90,
    doe_exim_loan_eligible: true,
    ndaa_defense_procurement_eligible: true
  });
  console.log('Niobium Verdict:', nb.audit_verdict?.status);
  console.log('DOE/EXIM Loan Eligible:', nb.audit_verdict?.doe_exim_loan_eligible);
}

main().catch(console.error);
