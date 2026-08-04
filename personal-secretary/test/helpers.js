const { WorkflowError } = require('../src/workflows/engine');

function createTestWorkflow(id, counters = { executions: 0 }) {
  return {
    id,
    async createProposal(input) {
      return { value: input.value };
    },
    validateProposal(proposal) {
      if (proposal.value !== 'ok') {
        throw new WorkflowError('quote_not_approved', 'proposal rejected');
      }
    },
    formatQuoteResponse({ proposal, quoteToken, quoteExpiresAt }) {
      return {
        proposal,
        quote_token: quoteToken,
        quote_expires_at: quoteExpiresAt,
        requires_confirmation: true,
      };
    },
    async execute(proposal) {
      counters.executions += 1;
      return { executed_value: proposal.value, execution_number: counters.executions };
    },
  };
}

module.exports = { createTestWorkflow };
