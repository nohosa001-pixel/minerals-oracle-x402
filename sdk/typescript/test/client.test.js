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
