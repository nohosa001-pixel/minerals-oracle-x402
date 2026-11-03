const test = require('node:test');
const assert = require('node:assert');
const { MineralsOracleClient } = require('../dist/index.js');

test('MineralsOracleClient exports and initialization (CJS)', (t) => {
  assert.strictEqual(typeof MineralsOracleClient, 'function');

  const client = new MineralsOracleClient({
    baseUrl: 'https://minerals-oracle-x402-7qxtp3324q-du.a.run.app',
    vaultKey: 'test-vault-key'
  });

  assert.strictEqual(client.baseUrl, 'https://minerals-oracle-x402-7qxtp3324q-du.a.run.app');
  assert.strictEqual(typeof client.getHealth, 'function');
  assert.strictEqual(typeof client.verifyTungsten, 'function');
  assert.strictEqual(typeof client.verifyRareEarths, 'function');
  assert.strictEqual(typeof client.verifyLithium, 'function');
  assert.strictEqual(typeof client.verifyNickel, 'function');
  assert.strictEqual(typeof client.verifyCobalt, 'function');
  assert.strictEqual(typeof client.verifyCopper, 'function');
  assert.strictEqual(typeof client.verifySilver, 'function');
  assert.strictEqual(typeof client.verifyNiobiumScandium, 'function');
  assert.strictEqual(typeof client.verifyCompositeBattery, 'function');
  assert.strictEqual(typeof client.proposeTradeDeal, 'function');
  assert.strictEqual(typeof client.dualSignTradeDeal, 'function');
  assert.strictEqual(typeof client.getTradeDeal, 'function');
  assert.strictEqual(typeof client.getEscrowCalldata, 'function');
  assert.strictEqual(typeof client.getMCPTools, 'function');
  assert.strictEqual(typeof client.harmonizeTradeFlow, 'function');
  assert.strictEqual(typeof client.generateTracesNtDds, 'function');
  assert.strictEqual(typeof client.settleUmpireAssay, 'function');
  assert.strictEqual(typeof client.getMultiChainGasBalances, 'function');
  assert.strictEqual(typeof client.getDeployedContracts, 'function');

  const contracts = client.getDeployedContracts();
  assert.strictEqual(contracts.polygon.tradeFinanceSettlementEngine, '0x1dD725fB4860e1e9E00aA887F4bda5acD3789d10');
  assert.strictEqual(contracts.base.tradeFinanceSettlementEngine, '0x9462587838fb8436C286AC9E04AAb6D42Eaf6D93');
  assert.strictEqual(contracts.arbitrum.tradeFinanceSettlementEngine, '0x402E95B6aE9BBD26A227A1AE2aC7f52E14E1A314');
  assert.strictEqual(contracts.creator, '0xA185B43fDD19619f99952AAed6eabf1029bF36a1');
});

test('MineralsOracleClient exports and initialization (ESM)', async (t) => {
  const esm = await import('../dist/index.mjs');
  assert.strictEqual(typeof esm.MineralsOracleClient, 'function');

  const client = new esm.MineralsOracleClient({
    baseUrl: 'https://minerals-oracle-x402-7qxtp3324q-du.a.run.app',
    vaultKey: 'test-vault-key'
  });

  assert.strictEqual(client.baseUrl, 'https://minerals-oracle-x402-7qxtp3324q-du.a.run.app');
  assert.strictEqual(typeof client.harmonizeTradeFlow, 'function');
});
