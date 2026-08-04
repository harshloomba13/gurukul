const test = require('node:test');
const assert = require('node:assert/strict');
const { MemoryAuditLogger, redact } = require('../src/audit');

test('audit redaction removes tokens and contact-like fields while preserving useful context', async () => {
  assert.deepEqual(redact({
    workflow_id: 'bakery_delivery',
    quote_token: 'secret-token',
    delivery_address: '123 Private St',
    nested: {
      email: 'person@example.com',
      total_cad: 26.78,
    },
  }), {
    workflow_id: 'bakery_delivery',
    quote_token: '[REDACTED]',
    delivery_address: '[REDACTED]',
    nested: {
      email: '[REDACTED]',
      total_cad: 26.78,
    },
  });

  const audit = new MemoryAuditLogger();
  await audit.record('workflow.quote.created', {
    quote_id: 'quote-1',
    api_key: 'secret-key',
    proposal: { delivery_destination_ref: 'home', total_cad: 26.78 },
  });
  assert.deepEqual(audit.records[0], {
    event: 'workflow.quote.created',
    quote_id: 'quote-1',
    api_key: '[REDACTED]',
    proposal: { delivery_destination_ref: 'home', total_cad: 26.78 },
  });
});
