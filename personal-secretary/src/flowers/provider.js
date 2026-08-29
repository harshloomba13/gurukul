const { isDeepStrictEqual } = require('node:util');
const { WorkflowError } = require('../workflows/errors');
const { buildFlowerProposal } = require('./domain');

class VjFlowerSubscriptionProvider {
  constructor({ fetchImpl = globalThis.fetch, timeoutMs = 12_000 } = {}) {
    if (typeof fetchImpl !== 'function') throw new Error('Flower provider requires fetch');
    this.fetchImpl = fetchImpl;
    this.timeoutMs = timeoutMs;
  }

  async loadCatalog(config) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), this.timeoutMs);
    timeout.unref?.();
    try {
      const response = await this.fetchImpl(config.product.productJsonUrl, {
        headers: { accept: 'application/json' },
        signal: controller.signal,
      });
      if (!response.ok) throw new Error(`Florist catalog returned HTTP ${response.status}`);
      return await response.json();
    } finally {
      clearTimeout(timeout);
    }
  }

  async createProposal(request, config) {
    return buildFlowerProposal(request, await this.loadCatalog(config), config);
  }

  async prepareCheckout(proposal, config) {
    const refreshed = buildFlowerProposal(
      { delivery_destination_ref: proposal.delivery_destination_ref },
      await this.loadCatalog(config),
      config,
    );
    if (!isDeepStrictEqual(refreshed, proposal)) {
      throw new WorkflowError(
        'quote_changed',
        'The florist availability, price, or subscription terms changed. Request a fresh quote.',
        409,
      );
    }
    return {
      workflow: 'flower_subscription',
      status: 'checkout_required',
      live_order: false,
      merchant: proposal.merchant,
      product: proposal.product,
      subscription: proposal.subscription,
      delivery_destination_ref: proposal.delivery_destination_ref,
      commitment_deliveries: proposal.commitment_deliveries,
      price_per_delivery_cad: proposal.price_per_delivery_cad,
      maximum_per_delivery_cad: proposal.maximum_per_delivery_cad,
      currency: proposal.currency,
      checkout_url: proposal.checkout_url,
      checkout_instructions: 'Select 3 Months and Monthly, then verify the final total and delivery details before paying.',
    };
  }
}

module.exports = { VjFlowerSubscriptionProvider };
