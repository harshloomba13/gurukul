const { WorkflowError } = require('../workflows/errors');
const {
  createConfiguredFlowerProposal,
  validateFlowerProposal,
  validateFlowerRequest,
} = require('./domain');

function createFlowerSubscriptionWorkflow({ config, provider }) {
  return {
    id: 'flower_subscription',
    quoteFailedCode: 'flower_quote_failed',
    executionFailedCode: 'flower_checkout_failed',

    async createProposal(input) {
      const request = validateFlowerRequest(input, config);
      const proposal = await provider.createProposal(request, config);
      validateFlowerProposal(proposal, config);
      return proposal;
    },

    validateProposal(proposal) {
      validateFlowerProposal(proposal, config);
    },

    toQuotePayload(basePayload, proposal) {
      return {
        ...basePayload,
        flower_quote: {
          delivery_destination_ref: proposal.delivery_destination_ref,
          price_per_delivery_cad: proposal.price_per_delivery_cad,
        },
      };
    },

    fromQuotePayload(payload) {
      return createConfiguredFlowerProposal({
        delivery_destination_ref: payload.flower_quote?.delivery_destination_ref,
      }, payload.flower_quote?.price_per_delivery_cad, config);
    },

    formatQuoteResponse({ proposal, quoteToken, quoteExpiresAt }) {
      return {
        workflow: 'flower_subscription',
        proposal,
        quote_token: quoteToken,
        quote_expires_at: quoteExpiresAt,
        requires_confirmation: true,
      };
    },

    async execute(proposal) {
      return provider.prepareCheckout(proposal, config);
    },

    auditProposal(proposal) {
      return {
        merchant: proposal.merchant,
        product: proposal.product,
        subscription: proposal.subscription,
        delivery_destination_ref: proposal.delivery_destination_ref,
        commitment_deliveries: proposal.commitment_deliveries,
        price_per_delivery_cad: proposal.price_per_delivery_cad,
        currency: proposal.currency,
      };
    },

    mapExecutionError(error) {
      if (error instanceof WorkflowError) return error;
      return new WorkflowError('flower_checkout_failed', error.message, 502);
    },
  };
}

module.exports = { createFlowerSubscriptionWorkflow };
