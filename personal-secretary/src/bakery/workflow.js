const { WorkflowError } = require('../workflows/errors');
const { validateBakeryProposal, validateBakeryRequest } = require('./domain');

function createBakeryWorkflow({ config, provider }) {
  return {
    id: 'bakery_delivery',
    quoteFailedCode: 'bakery_quote_failed',
    executionFailedCode: 'bakery_order_failed',

    async createProposal(input) {
      const request = validateBakeryRequest(input, config);
      const proposal = await provider.createProposal(request, config);
      validateBakeryProposal(proposal, config);
      return proposal;
    },

    validateProposal(proposal) {
      validateBakeryProposal(proposal, config);
    },

    formatQuoteResponse({ proposal, quoteToken, quoteExpiresAt }) {
      return {
        workflow: 'bakery_delivery',
        proposal,
        quote_token: quoteToken,
        quote_expires_at: quoteExpiresAt,
        requires_confirmation: true,
      };
    },

    async execute(proposal) {
      return provider.placeOrder(proposal);
    },

    auditProposal(proposal) {
      return {
        merchant: proposal.merchant,
        products: proposal.products,
        delivery_destination_ref: proposal.delivery_destination_ref,
        delivery_window: proposal.delivery_window,
        total_estimated_cad: proposal.total_estimated_cad,
        currency: proposal.currency,
      };
    },

    mapExecutionError(error) {
      if (error instanceof WorkflowError) return error;
      return new WorkflowError('bakery_order_failed', error.message, 502);
    },
  };
}

module.exports = { createBakeryWorkflow };
