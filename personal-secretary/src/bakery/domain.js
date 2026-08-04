const { WorkflowError } = require('../workflows/errors');

const REQUEST_KEYS = new Set([
  'delivery_destination_ref',
  'delivery_window',
  'merchant_id',
  'products',
  'tip_cad',
]);
const MERCHANT_KEYS = new Set(['id', 'name']);
const PRODUCT_KEYS = new Set(['line_total_cad', 'name', 'quantity', 'sku', 'unit_price_cad']);
const WINDOW_KEYS = new Set(['id', 'label']);
const FEES_KEYS = new Set(['delivery_cad']);
const PROPOSAL_KEYS = new Set([
  'currency',
  'delivery_destination_ref',
  'delivery_window',
  'fees',
  'live_order',
  'merchant',
  'products',
  'provider',
  'subtotal_cad',
  'tax_cad',
  'tip_cad',
  'total_estimated_cad',
  'workflow',
]);

function fail(code, message, status = 400) {
  throw new WorkflowError(code, message, status);
}

function assertPlainObject(value, code, message) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    fail(code, message);
  }
}

function assertAllowedKeys(value, allowedKeys, code, label) {
  for (const key of Object.keys(value)) {
    if (!allowedKeys.has(key)) fail(code, `${label} contains unsupported field: ${key}`);
  }
}

function toCents(value) {
  if (typeof value !== 'number' || !Number.isFinite(value)) return null;
  return Math.round(value * 100);
}

function fromCents(value) {
  return Number((value / 100).toFixed(2));
}

function requireCad(value, expectedCents, fieldName, code = 'quote_not_approved') {
  const cents = toCents(value);
  if (cents === null || cents !== expectedCents) {
    fail(code, `${fieldName} does not match the configured bakery quote.`);
  }
}

function productBySku(config, sku) {
  return config.products.find(product => product.sku === sku);
}

function normalizeDeliveryWindow(input, config) {
  const windowId = input.delivery_window || config.defaultDeliveryWindow;
  const window = config.deliveryWindows.find(candidate => candidate.id === windowId);
  if (!window) fail('invalid_delivery_window', 'Requested delivery window is not configured.');
  return window;
}

function validateBakeryRequest(input, config) {
  assertPlainObject(input, 'invalid_request', 'Bakery quote request must be an object.');
  assertAllowedKeys(input, REQUEST_KEYS, 'invalid_request', 'Bakery quote request');

  if (input.merchant_id && input.merchant_id !== config.merchant.id) {
    fail('invalid_merchant', 'Requested merchant is not configured for this workflow.');
  }
  if (!Array.isArray(input.products) || input.products.length === 0) {
    fail('invalid_products', 'At least one bakery product is required.');
  }
  if (!config.deliveryDestinationRefs.includes(input.delivery_destination_ref)) {
    fail('invalid_delivery_destination', 'Delivery destination reference is not configured.');
  }

  let totalQuantity = 0;
  const products = input.products.map((item, index) => {
    assertPlainObject(item, 'invalid_products', `Product ${index + 1} must be an object.`);
    assertAllowedKeys(item, new Set(['quantity', 'sku']), 'invalid_products', `Product ${index + 1}`);
    const configured = productBySku(config, item.sku);
    if (!configured) fail('invalid_products', `Product is not configured: ${item.sku}`);
    if (!Number.isInteger(item.quantity) || item.quantity < 1 || item.quantity > configured.maxQuantity) {
      fail('invalid_quantity', `Quantity for ${item.sku} must be between 1 and ${configured.maxQuantity}.`);
    }
    totalQuantity += item.quantity;
    return { sku: item.sku, quantity: item.quantity };
  });
  if (totalQuantity > config.maxTotalQuantity) {
    fail('invalid_quantity', `Total quantity must be ${config.maxTotalQuantity} items or fewer.`);
  }

  const tipCad = input.tip_cad ?? 0;
  const tipCents = toCents(tipCad);
  if (tipCents === null || tipCents < 0) fail('invalid_tip', 'Tip must be a non-negative CAD amount.');
  if (!config.tip.enabled && tipCents > 0) fail('invalid_tip', 'Tip is not enabled for this workflow.');
  if (config.tip.enabled && tipCents > toCents(config.tip.maxCad)) {
    fail('invalid_tip', `Tip must be ${config.tip.maxCad} CAD or less.`);
  }

  return {
    merchant_id: input.merchant_id || config.merchant.id,
    products,
    delivery_destination_ref: input.delivery_destination_ref,
    delivery_window: normalizeDeliveryWindow(input, config),
    tip_cad: fromCents(tipCents),
  };
}

function buildBakeryProposal(request, config) {
  const products = request.products.map(item => {
    const configured = productBySku(config, item.sku);
    const unitCents = toCents(configured.unitPriceCad);
    const lineCents = unitCents * item.quantity;
    return {
      sku: configured.sku,
      name: configured.name,
      quantity: item.quantity,
      unit_price_cad: fromCents(unitCents),
      line_total_cad: fromCents(lineCents),
    };
  });
  const subtotalCents = products.reduce((sum, item) => sum + toCents(item.line_total_cad), 0);
  const deliveryCents = toCents(config.deliveryFeeCad);
  const tipCents = toCents(request.tip_cad);
  const taxableCents = subtotalCents + deliveryCents + tipCents;
  const taxCents = Math.round(taxableCents * config.taxRate);
  const totalCents = taxableCents + taxCents;
  if (totalCents > toCents(config.spendingLimitCad)) {
    fail('spending_limit_exceeded', `Estimated bakery total exceeds ${config.spendingLimitCad} CAD.`);
  }

  return {
    workflow: 'bakery_delivery',
    provider: 'fake_bakery',
    live_order: false,
    merchant: { ...config.merchant },
    products,
    delivery_destination_ref: request.delivery_destination_ref,
    delivery_window: { ...request.delivery_window },
    fees: { delivery_cad: fromCents(deliveryCents) },
    subtotal_cad: fromCents(subtotalCents),
    tax_cad: fromCents(taxCents),
    tip_cad: fromCents(tipCents),
    total_estimated_cad: fromCents(totalCents),
    currency: 'CAD',
  };
}

function validateBakeryProposal(proposal, config) {
  assertPlainObject(proposal, 'quote_not_approved', 'Bakery quote proposal must be an object.');
  assertAllowedKeys(proposal, PROPOSAL_KEYS, 'quote_not_approved', 'Bakery quote proposal');
  assertPlainObject(proposal.merchant, 'quote_not_approved', 'Bakery merchant must be an object.');
  assertAllowedKeys(proposal.merchant, MERCHANT_KEYS, 'quote_not_approved', 'Bakery merchant');
  assertPlainObject(proposal.delivery_window, 'quote_not_approved', 'Bakery delivery window must be an object.');
  assertAllowedKeys(proposal.delivery_window, WINDOW_KEYS, 'quote_not_approved', 'Bakery delivery window');
  assertPlainObject(proposal.fees, 'quote_not_approved', 'Bakery fees must be an object.');
  assertAllowedKeys(proposal.fees, FEES_KEYS, 'quote_not_approved', 'Bakery fees');

  if (proposal.workflow !== 'bakery_delivery' || proposal.provider !== 'fake_bakery' || proposal.live_order !== false) {
    fail('quote_not_approved', 'Bakery quote provider is not approved.');
  }
  if (proposal.currency !== 'CAD') fail('quote_not_approved', 'Bakery quote currency is not approved.');
  if (proposal.merchant.id !== config.merchant.id || proposal.merchant.name !== config.merchant.name) {
    fail('quote_not_approved', 'Bakery quote merchant is not configured.');
  }
  if (!config.deliveryDestinationRefs.includes(proposal.delivery_destination_ref)) {
    fail('quote_not_approved', 'Bakery quote delivery destination reference is not configured.');
  }
  const configuredWindow = config.deliveryWindows.find(window => window.id === proposal.delivery_window.id);
  if (!configuredWindow || configuredWindow.label !== proposal.delivery_window.label) {
    fail('quote_not_approved', 'Bakery quote delivery window is not configured.');
  }
  if (!Array.isArray(proposal.products) || proposal.products.length === 0) {
    fail('quote_not_approved', 'Bakery quote must contain products.');
  }

  let totalQuantity = 0;
  let subtotalCents = 0;
  for (const item of proposal.products) {
    assertPlainObject(item, 'quote_not_approved', 'Bakery quote product must be an object.');
    assertAllowedKeys(item, PRODUCT_KEYS, 'quote_not_approved', 'Bakery quote product');
    const configured = productBySku(config, item.sku);
    if (!configured || item.name !== configured.name) {
      fail('quote_not_approved', `Bakery quote product is not configured: ${item.sku}`);
    }
    if (!Number.isInteger(item.quantity) || item.quantity < 1 || item.quantity > configured.maxQuantity) {
      fail('quote_not_approved', `Bakery quote quantity is not configured: ${item.sku}`);
    }
    totalQuantity += item.quantity;
    const unitCents = toCents(configured.unitPriceCad);
    requireCad(item.unit_price_cad, unitCents, 'Bakery product price');
    const lineCents = unitCents * item.quantity;
    requireCad(item.line_total_cad, lineCents, 'Bakery line total');
    subtotalCents += lineCents;
  }
  if (totalQuantity > config.maxTotalQuantity) {
    fail('quote_not_approved', 'Bakery quote exceeds the configured quantity limit.');
  }

  const deliveryCents = toCents(config.deliveryFeeCad);
  const tipCents = toCents(proposal.tip_cad);
  if (tipCents === null || tipCents < 0) fail('quote_not_approved', 'Bakery quote tip is not approved.');
  if (!config.tip.enabled && tipCents > 0) fail('quote_not_approved', 'Bakery quote tip is not enabled.');
  if (config.tip.enabled && tipCents > toCents(config.tip.maxCad)) {
    fail('quote_not_approved', 'Bakery quote tip exceeds the configured limit.');
  }
  const taxCents = Math.round((subtotalCents + deliveryCents + tipCents) * config.taxRate);
  const totalCents = subtotalCents + deliveryCents + tipCents + taxCents;
  requireCad(proposal.fees.delivery_cad, deliveryCents, 'Bakery delivery fee');
  requireCad(proposal.subtotal_cad, subtotalCents, 'Bakery subtotal');
  requireCad(proposal.tax_cad, taxCents, 'Bakery tax');
  requireCad(proposal.total_estimated_cad, totalCents, 'Bakery total');
  if (totalCents > toCents(config.spendingLimitCad)) {
    fail('spending_limit_exceeded', `Estimated bakery total exceeds ${config.spendingLimitCad} CAD.`);
  }
}

function canonicalJson(value) {
  if (Array.isArray(value)) return `[${value.map(canonicalJson).join(',')}]`;
  if (value && typeof value === 'object') {
    return `{${Object.keys(value).sort().map(key => `${JSON.stringify(key)}:${canonicalJson(value[key])}`).join(',')}}`;
  }
  return JSON.stringify(value);
}

module.exports = {
  buildBakeryProposal,
  canonicalJson,
  validateBakeryProposal,
  validateBakeryRequest,
};
