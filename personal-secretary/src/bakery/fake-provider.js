const crypto = require('crypto');
const { buildBakeryProposal, canonicalJson } = require('./domain');

class FakeBakeryProvider {
  constructor({ failQuote = false, failOrder = false } = {}) {
    this.failQuote = failQuote;
    this.failOrder = failOrder;
    this.orderAttempts = 0;
  }

  async createProposal(request, config) {
    if (this.failQuote) throw new Error('Fake bakery provider failed to quote');
    return buildBakeryProposal(request, config);
  }

  async placeOrder(proposal) {
    this.orderAttempts += 1;
    if (this.failOrder) throw new Error('Fake bakery provider failed to place order');
    const digest = crypto.createHash('sha256').update(canonicalJson(proposal)).digest('hex').slice(0, 12);
    return {
      workflow: 'bakery_delivery',
      order_id: `fake-bakery-${digest}`,
      status: 'accepted_sandbox',
      live_order: false,
      merchant: proposal.merchant,
      products: proposal.products,
      delivery_destination_ref: proposal.delivery_destination_ref,
      delivery_window: proposal.delivery_window,
      total_cad: proposal.total_estimated_cad,
      currency: proposal.currency,
      provider_reference: 'fake_bakery',
    };
  }
}

module.exports = { FakeBakeryProvider };
