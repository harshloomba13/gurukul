const test = require('node:test');
const assert = require('node:assert/strict');
const { DEFAULTS } = require('../src/config');
const { VjFlowerSubscriptionProvider } = require('../src/flowers/provider');
const { createFlowerSubscriptionWorkflow } = require('../src/flowers/workflow');
const { WorkflowEngine } = require('../src/workflows/engine');

function catalog(overrides = {}) {
  const price = overrides.price ?? 7199;
  return {
    id: 8890663731456,
    title: 'Classic Floral Subscription',
    available: overrides.available ?? true,
    variants: [{
      id: 46146231533824,
      title: '3 Months',
      available: overrides.variantAvailable ?? true,
      requires_selling_plan: true,
      selling_plan_allocations: [{
        selling_plan_id: 4019519744,
        price,
        per_delivery_price: price,
      }],
    }],
    selling_plan_groups: [{
      selling_plans: [{
        id: 4019519744,
        name: 'Monthly (3 Month)',
        recurring_deliveries: true,
        options: [{ value: 'Every month' }],
      }],
    }],
  };
}

function response(body) {
  return { ok: true, status: 200, async json() { return body; } };
}

function createEngine(fetchImpl) {
  const provider = new VjFlowerSubscriptionProvider({ fetchImpl });
  return new WorkflowEngine({
    workflows: [createFlowerSubscriptionWorkflow({ config: DEFAULTS.flowers, provider })],
    signingKey: 'secret',
    quoteTtlSeconds: 10,
    nowSeconds: () => 100,
    idFactory: () => 'quote-id',
  });
}

test('flower workflow quotes the approved monthly plan under the budget cap', async () => {
  const engine = createEngine(async () => response(catalog()));
  const quote = await engine.createQuote('flower_subscription', {});

  assert.equal(quote.workflow, 'flower_subscription');
  assert.equal(quote.requires_confirmation, true);
  assert.equal(quote.proposal.merchant.name, 'V&J Plant Shop');
  assert.equal(quote.proposal.product.variant_title, '3 Months');
  assert.equal(quote.proposal.subscription.name, 'Monthly (3 Month)');
  assert.equal(quote.proposal.delivery_destination_ref, 'wife_home');
  assert.equal(quote.proposal.price_per_delivery_cad, 71.99);
  assert.equal(quote.proposal.maximum_per_delivery_cad, 80);
  assert.equal(quote.proposal.live_order, false);
  assert.ok(quote.quote_token.length < 700, `Expected compact quote token, got ${quote.quote_token.length} chars`);
});

test('flower execution rechecks the catalog and returns checkout_required without placing an order', async () => {
  let fetches = 0;
  const engine = createEngine(async () => {
    fetches += 1;
    return response(catalog());
  });
  const quote = await engine.createQuote('flower_subscription', {});
  const result = await engine.execute('flower_subscription', {
    quote_token: quote.quote_token,
    confirm: true,
  });

  assert.equal(fetches, 2);
  assert.equal(result.status, 'checkout_required');
  assert.equal(result.live_order, false);
  assert.equal(result.price_per_delivery_cad, 71.99);
  assert.match(result.checkout_url, /^https:\/\/vjplantshop\.com\//);
  assert.equal('order_id' in result, false);
});

test('flower workflow rejects raw fields, unknown destinations, over-budget prices, and unavailable plans', async () => {
  const engine = createEngine(async () => response(catalog()));
  await assert.rejects(
    () => engine.createQuote('flower_subscription', { address: 'raw-address' }),
    error => error.code === 'invalid_request',
  );
  await assert.rejects(
    () => engine.createQuote('flower_subscription', { delivery_destination_ref: 'office' }),
    error => error.code === 'invalid_delivery_destination',
  );

  const expensive = createEngine(async () => response(catalog({ price: 8100 })));
  await assert.rejects(
    () => expensive.createQuote('flower_subscription', {}),
    error => error.code === 'spending_limit_exceeded',
  );

  const unavailable = createEngine(async () => response(catalog({ variantAvailable: false })));
  await assert.rejects(
    () => unavailable.createQuote('flower_subscription', {}),
    error => error.code === 'flower_unavailable',
  );
});

test('flower execution rejects a changed price and does not reuse the stale quote', async () => {
  let fetches = 0;
  const engine = createEngine(async () => {
    fetches += 1;
    return response(catalog({ price: fetches === 1 ? 7199 : 7499 }));
  });
  const quote = await engine.createQuote('flower_subscription', {});

  await assert.rejects(
    () => engine.execute('flower_subscription', { quote_token: quote.quote_token, confirm: true }),
    error => error.code === 'quote_changed',
  );
});
