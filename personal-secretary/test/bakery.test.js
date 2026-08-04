const test = require('node:test');
const assert = require('node:assert/strict');
const { DEFAULTS } = require('../src/config');
const { FakeBakeryProvider } = require('../src/bakery/fake-provider');
const { createBakeryWorkflow } = require('../src/bakery/workflow');
const { buildBakeryProposal, validateBakeryRequest } = require('../src/bakery/domain');
const { WorkflowEngine } = require('../src/workflows/engine');
const { createTestWorkflow } = require('./helpers');
const { signQuote } = require('../src/quote');

function createBakeryEngine(provider, nowSeconds = () => 100) {
  return new WorkflowEngine({
    workflows: [
      createBakeryWorkflow({ config: DEFAULTS.bakery, provider }),
      createTestWorkflow('haircut'),
    ],
    signingKey: 'secret',
    quoteTtlSeconds: 10,
    nowSeconds,
    idFactory: () => 'quote-id',
  });
}

function validRequest(overrides = {}) {
  return {
    merchant_id: 'sandbox-bakery',
    products: [{ sku: 'sourdough-loaf', quantity: 2 }],
    delivery_destination_ref: 'home',
    delivery_window: 'today_4_6_pm',
    tip_cad: 2,
    ...overrides,
  };
}

test('bakery workflow returns a safe quote and executes a deterministic sandbox order', async () => {
  const provider = new FakeBakeryProvider();
  const engine = createBakeryEngine(provider);

  const quote = await engine.createQuote('bakery_delivery', validRequest());
  assert.equal(quote.workflow, 'bakery_delivery');
  assert.equal(quote.requires_confirmation, true);
  assert.equal(quote.proposal.live_order, false);
  assert.equal(quote.proposal.merchant.name, 'Sandbox Bakery');
  assert.equal(quote.proposal.delivery_destination_ref, 'home');
  assert.equal(quote.proposal.total_estimated_cad, 26.78);

  const result = await engine.execute('bakery_delivery', {
    quote_token: quote.quote_token,
    confirm: true,
  });
  assert.equal(result.idempotent_replay, false);
  assert.equal(result.status, 'accepted_sandbox');
  assert.equal(result.live_order, false);
  assert.equal(result.total_cad, 26.78);
  assert.match(result.order_id, /^fake-bakery-/);
});

test('bakery execution is idempotent for repeated quote execution', async () => {
  const provider = new FakeBakeryProvider();
  const engine = createBakeryEngine(provider);
  const quote = await engine.createQuote('bakery_delivery', validRequest());

  const first = await engine.execute('bakery_delivery', { quote_token: quote.quote_token, confirm: true });
  const second = await engine.execute('bakery_delivery', { quote_token: quote.quote_token, confirm: true });

  assert.equal(first.order_id, second.order_id);
  assert.equal(second.idempotent_replay, true);
  assert.equal(provider.orderAttempts, 1);
});

test('bakery quote validation rejects invalid products, quantities, delivery refs, and spending violations', async () => {
  const engine = createBakeryEngine(new FakeBakeryProvider());

  await assert.rejects(
    () => engine.createQuote('bakery_delivery', validRequest({ products: [{ sku: 'bagel', quantity: 1 }] })),
    error => error.code === 'invalid_products',
  );
  await assert.rejects(
    () => engine.createQuote('bakery_delivery', validRequest({ products: [{ sku: 'sourdough-loaf', quantity: 5 }] })),
    error => error.code === 'invalid_quantity',
  );
  await assert.rejects(
    () => engine.createQuote('bakery_delivery', validRequest({ delivery_destination_ref: 'raw-address' })),
    error => error.code === 'invalid_delivery_destination',
  );
  await assert.rejects(
    () => engine.createQuote('bakery_delivery', validRequest({
      products: [
        { sku: 'croissant-box-6', quantity: 2 },
        { sku: 'cinnamon-roll-box-4', quantity: 3 },
      ],
    })),
    error => error.code === 'spending_limit_exceeded',
  );
});

test('bakery execution rejects expired, mismatched, tampered, and modified signed quotes', async () => {
  let now = 100;
  const engine = createBakeryEngine(new FakeBakeryProvider(), () => now);
  const quote = await engine.createQuote('bakery_delivery', validRequest());

  await assert.rejects(
    () => engine.execute('bakery_delivery', { quote_token: `${quote.quote_token.slice(0, -1)}x`, confirm: true }),
    error => error.code === 'invalid_quote',
  );
  await assert.rejects(
    () => engine.execute('haircut', { quote_token: quote.quote_token, confirm: true }),
    error => error.code === 'quote_workflow_mismatch',
  );
  const wrongWorkflowQuote = signQuote({
    version: 1,
    workflow_id: 'haircut',
    quote_id: 'wrong',
    expires_at: 200,
    proposal: quote.proposal,
  }, 'secret');
  await assert.rejects(
    () => engine.execute('bakery_delivery', { quote_token: wrongWorkflowQuote, confirm: true }),
    error => error.code === 'quote_workflow_mismatch',
  );

  const request = validateBakeryRequest(validRequest(), DEFAULTS.bakery);
  const modifiedProposal = buildBakeryProposal(request, DEFAULTS.bakery);
  modifiedProposal.products[0].quantity = 3;
  const modifiedSignedQuote = signQuote({
    version: 1,
    workflow_id: 'bakery_delivery',
    quote_id: 'modified',
    expires_at: 200,
    proposal: modifiedProposal,
  }, 'secret');
  await assert.rejects(
    () => engine.execute('bakery_delivery', { quote_token: modifiedSignedQuote, confirm: true }),
    error => error.code === 'quote_not_approved',
  );

  now = 111;
  await assert.rejects(
    () => engine.execute('bakery_delivery', { quote_token: quote.quote_token, confirm: true }),
    error => error.code === 'invalid_quote' && /expired/i.test(error.message),
  );
});

test('bakery provider failures do not cache a completed order', async () => {
  const provider = new FakeBakeryProvider({ failOrder: true });
  const engine = createBakeryEngine(provider);
  const quote = await engine.createQuote('bakery_delivery', validRequest());

  await assert.rejects(
    () => engine.execute('bakery_delivery', { quote_token: quote.quote_token, confirm: true }),
    error => error.code === 'bakery_order_failed',
  );
  assert.equal(provider.orderAttempts, 1);
});
