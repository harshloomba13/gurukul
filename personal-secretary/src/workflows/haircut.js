const { getAvailability, bookExactSlot } = require('../delray');
const { WorkflowError } = require('./errors');

function normalizeSearchWeeks(input, config) {
  const requested = input?.max_weeks ?? config.defaultSearchWeeks;
  const numeric = Number(requested);
  if (!Number.isFinite(numeric)) {
    throw new WorkflowError('invalid_request', 'max_weeks must be a number.', 400);
  }
  return Math.min(Math.max(Math.trunc(numeric), 1), config.maxWeeks);
}

function validateHaircutSlot(slot, config) {
  const approved = slot
    && slot.business === config.businessName
    && slot.service === config.serviceName
    && slot.staff === config.staffName
    && slot.dueTodayCad === 0
    && typeof slot.dateLabel === 'string'
    && typeof slot.timeLabel === 'string';
  if (!approved) {
    throw new WorkflowError('quote_not_approved', 'Quote does not match the approved haircut workflow.', 400);
  }
}

function createHaircutWorkflow({ config }) {
  return {
    id: 'haircut',
    acceptsLegacyQuote: true,
    quoteFailedCode: 'availability_failed',
    executionFailedCode: 'booking_failed',

    async createProposal(input) {
      const maxWeeks = normalizeSearchWeeks(input, config);
      console.log(`Availability search requested for ${maxWeeks} week(s)`);
      const slot = await getAvailability(config, maxWeeks);
      if (!slot) {
        throw new WorkflowError(
          'no_availability',
          `No Thursday or Friday appointment after 2:00 PM was found in the next ${maxWeeks} weeks.`,
          404,
        );
      }
      return slot;
    },

    validateProposal(slot) {
      validateHaircutSlot(slot, config);
    },

    toQuotePayload(basePayload, slot) {
      return { ...basePayload, slot };
    },

    fromQuotePayload(payload) {
      return payload.slot;
    },

    formatQuoteResponse({ proposal, quoteToken, quoteExpiresAt }) {
      return {
        slot: proposal,
        quote_token: quoteToken,
        quote_expires_at: quoteExpiresAt,
        requires_confirmation: true,
      };
    },

    async execute(slot) {
      return bookExactSlot(config, {
        dateLabel: slot.dateLabel,
        timeLabel: slot.timeLabel,
      });
    },

    mapExecutionError(error) {
      if (error.code === 'SLOT_UNAVAILABLE') {
        return new WorkflowError('slot_unavailable', error.message, 409);
      }
      return new WorkflowError('booking_failed', error.message, 502);
    },
  };
}

module.exports = { createHaircutWorkflow, normalizeSearchWeeks, validateHaircutSlot };
