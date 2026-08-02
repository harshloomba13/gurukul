const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs/promises');
const os = require('os');
const path = require('path');
const { signQuote, verifyQuote } = require('../src/quote');
const { EncryptedSessionStore } = require('../src/session-store');
const { ExecutorService } = require('../src/service');

test('quote signatures reject tampering and expiration', () => {
  const token = signQuote({ version: 1, id: 'quote', summary: { total: 1 }, expiresAt: 200 }, 'key');
  assert.equal(verifyQuote(token, 'key', 100).expiresAt, 200);
  assert.throws(() => verifyQuote(`${token}x`, 'key', 100), /signature/);
  assert.throws(() => verifyQuote(token, 'key', 201), /expired/);
  assert.throws(() => verifyQuote(signQuote({ expiresAt: 200 }, 'key'), 'key', 100), /payload/);
});

test('session state is encrypted at rest', async () => {
  const dir = await fs.mkdtemp(path.join(os.tmpdir(), 'executor-'));
  const store = new EncryptedSessionStore(dir, 'test-key');
  await store.put('quote', { cookie: 'sensitive-value' });
  assert.deepEqual(await store.get('quote'), { cookie: 'sensitive-value' });
  assert.doesNotMatch((await fs.readFile(store.file('quote'))).toString(), /sensitive-value/);
});

test('approval requires confirmation and is idempotent', async () => {
  let purchases = 0;
  const states = new Map();
  const service = new ExecutorService({
    adapter: { prepare: async () => ({ summary: { total: 10 }, state: { cookie: 1 } }), purchase: async () => ({ orderId: `order-${++purchases}` }) },
    sessions: { put: async (k, v) => states.set(k, v), get: async k => states.get(k) },
    audit: { record: async () => {} }, signingKey: 'key', quoteTtlMs: 10000,
  });
  const prepared = await service.prepare({});
  await assert.rejects(service.approve({ quoteToken: prepared.quoteToken, approve: false, idempotencyKey: 'one' }), /approval/);
  const first = await service.approve({ quoteToken: prepared.quoteToken, approve: true, idempotencyKey: 'one' });
  const second = await service.approve({ quoteToken: prepared.quoteToken, approve: true, idempotencyKey: 'one' });
  assert.equal(first.orderId, second.orderId);
  assert.equal(second.idempotentReplay, true);
  assert.equal(purchases, 1);

  const another = await service.prepare({});
  await assert.rejects(
    service.approve({ quoteToken: another.quoteToken, approve: true, idempotencyKey: 'one' }),
    /another quote/,
  );
  assert.equal(purchases, 1);
});
