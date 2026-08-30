const { WorkflowError } = require('../workflows/errors');

const REQUEST_KEYS = new Set(['delivery_destination_ref']);
const PROPOSAL_KEYS = new Set([
  'cadence',
  'commitment_deliveries',
  'currency',
  'delivery_destination_ref',
  'live_order',
  'maximum_per_delivery_cad',
  'merchant',
  'price_per_delivery_cad',
  'product',
  'provider',
  'requires_checkout',
  'subscription',
  'workflow',
  'checkout_url',
]);
const MERCHANT_KEYS = new Set(['id', 'location', 'name']);
const PRODUCT_KEYS = new Set(['id', 'title', 'variant_id', 'variant_title']);
const SUBSCRIPTION_KEYS = new Set(['frequency', 'name', 'selling_plan_id']);

function fail(code, message, status = 400) {
  throw new WorkflowError(code, message, status);
}

function assertPlainObject(value, code, message) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) fail(code, message);
}

function assertAllowedKeys(value, allowedKeys, code, label) {
  for (const key of Object.keys(value)) {
    if (!allowedKeys.has(key)) fail(code, `${label} contains unsupported field: ${key}`);
  }
}

function fromCents(value) {
  return Number((value / 100).toFixed(2));
}

function toCents(value) {
  if (typeof value !== 'number' || !Number.isFinite(value)) return null;
  return Math.round(value * 100);
}

function validateFlowerRequest(input, config) {
  assertPlainObject(input, 'invalid_request', 'Flower subscription quote request must be an object.');
  assertAllowedKeys(input, REQUEST_KEYS, 'invalid_request', 'Flower subscription quote request');
  const destination = input.delivery_destination_ref || config.defaultDeliveryDestinationRef;
  if (!config.deliveryDestinationRefs.includes(destination)) {
    fail('invalid_delivery_destination', 'Delivery destination reference is not configured.');
  }
  return { delivery_destination_ref: destination };
}

function findConfiguredCatalogSelection(catalog, config) {
  if (!catalog || catalog.id !== config.product.id || catalog.title !== config.product.title || !catalog.available) {
    fail('flower_unavailable', 'The configured floral subscription is unavailable.', 409);
  }
  const variant = (catalog.variants || []).find(candidate => candidate.id === config.product.variantId);
  if (!variant || variant.title !== config.product.variantTitle || !variant.available || !variant.requires_selling_plan) {
    fail('flower_unavailable', 'The configured three-month floral subscription is unavailable.', 409);
  }
  const group = (catalog.selling_plan_groups || []).find(candidate =>
    (candidate.selling_plans || []).some(plan => plan.id === config.product.sellingPlanId));
  const plan = group?.selling_plans?.find(candidate => candidate.id === config.product.sellingPlanId);
  const allocation = (variant.selling_plan_allocations || []).find(candidate =>
    candidate.selling_plan_id === config.product.sellingPlanId);
  if (!plan || plan.name !== config.product.sellingPlanName || !plan.recurring_deliveries || !allocation) {
    fail('flower_unavailable', 'The configured monthly selling plan is unavailable.', 409);
  }
  const monthlyOption = (plan.options || []).some(option => option.value === 'Every month');
  if (!monthlyOption) fail('flower_unavailable', 'The configured selling plan is no longer monthly.', 409);
  const priceCents = allocation.per_delivery_price ?? allocation.price;
  if (!Number.isInteger(priceCents) || priceCents <= 0) {
    fail('flower_quote_failed', 'The florist returned an invalid subscription price.', 502);
  }
  if (priceCents > toCents(config.spendingLimitCad)) {
    fail(
      'spending_limit_exceeded',
      `The floral subscription exceeds the ${config.spendingLimitCad} CAD per-delivery limit.`,
      409,
    );
  }
  return { priceCents };
}

function createConfiguredFlowerProposal(request, pricePerDeliveryCad, config) {
  return {
    workflow: 'flower_subscription',
    provider: 'vj_shopify_checkout',
    live_order: false,
    merchant: { ...config.merchant },
    product: {
      id: config.product.id,
      title: config.product.title,
      variant_id: config.product.variantId,
      variant_title: config.product.variantTitle,
    },
    subscription: {
      selling_plan_id: config.product.sellingPlanId,
      name: config.product.sellingPlanName,
      frequency: config.cadence,
    },
    delivery_destination_ref: request.delivery_destination_ref,
    cadence: config.cadence,
    commitment_deliveries: config.commitmentDeliveries,
    price_per_delivery_cad: pricePerDeliveryCad,
    maximum_per_delivery_cad: config.spendingLimitCad,
    currency: 'CAD',
    requires_checkout: true,
    checkout_url: config.product.checkoutUrl,
  };
}

function buildFlowerProposal(request, catalog, config) {
  const { priceCents } = findConfiguredCatalogSelection(catalog, config);
  return createConfiguredFlowerProposal(request, fromCents(priceCents), config);
}

function validateFlowerProposal(proposal, config) {
  assertPlainObject(proposal, 'quote_not_approved', 'Flower subscription proposal must be an object.');
  assertAllowedKeys(proposal, PROPOSAL_KEYS, 'quote_not_approved', 'Flower subscription proposal');
  assertPlainObject(proposal.merchant, 'quote_not_approved', 'Flower merchant must be an object.');
  assertAllowedKeys(proposal.merchant, MERCHANT_KEYS, 'quote_not_approved', 'Flower merchant');
  assertPlainObject(proposal.product, 'quote_not_approved', 'Flower product must be an object.');
  assertAllowedKeys(proposal.product, PRODUCT_KEYS, 'quote_not_approved', 'Flower product');
  assertPlainObject(proposal.subscription, 'quote_not_approved', 'Flower subscription must be an object.');
  assertAllowedKeys(proposal.subscription, SUBSCRIPTION_KEYS, 'quote_not_approved', 'Flower subscription');

  if (proposal.workflow !== 'flower_subscription'
    || proposal.provider !== 'vj_shopify_checkout'
    || proposal.live_order !== false
    || proposal.requires_checkout !== true) {
    fail('quote_not_approved', 'Flower subscription provider is not approved.');
  }
  if (proposal.currency !== 'CAD'
    || proposal.cadence !== config.cadence
    || proposal.commitment_deliveries !== config.commitmentDeliveries) {
    fail('quote_not_approved', 'Flower subscription terms are not approved.');
  }
  for (const key of ['id', 'name', 'location']) {
    if (proposal.merchant[key] !== config.merchant[key]) fail('quote_not_approved', 'Flower merchant is not configured.');
  }
  if (proposal.product.id !== config.product.id
    || proposal.product.title !== config.product.title
    || proposal.product.variant_id !== config.product.variantId
    || proposal.product.variant_title !== config.product.variantTitle) {
    fail('quote_not_approved', 'Flower product is not configured.');
  }
  if (proposal.subscription.selling_plan_id !== config.product.sellingPlanId
    || proposal.subscription.name !== config.product.sellingPlanName
    || proposal.subscription.frequency !== config.cadence) {
    fail('quote_not_approved', 'Flower selling plan is not configured.');
  }
  if (!config.deliveryDestinationRefs.includes(proposal.delivery_destination_ref)) {
    fail('quote_not_approved', 'Flower delivery destination reference is not configured.');
  }
  const priceCents = toCents(proposal.price_per_delivery_cad);
  const limitCents = toCents(config.spendingLimitCad);
  if (priceCents === null || priceCents <= 0 || priceCents > limitCents
    || toCents(proposal.maximum_per_delivery_cad) !== limitCents) {
    fail('spending_limit_exceeded', `Flower price must be within ${config.spendingLimitCad} CAD per delivery.`, 409);
  }
  if (proposal.checkout_url !== config.product.checkoutUrl) {
    fail('quote_not_approved', 'Flower checkout URL is not approved.');
  }
}

module.exports = {
  buildFlowerProposal,
  createConfiguredFlowerProposal,
  validateFlowerProposal,
  validateFlowerRequest,
};
