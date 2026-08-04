const test = require('node:test');
const assert = require('node:assert/strict');
const { MemoryAuditLogger } = require('../src/audit');
const { WorkflowEngine } = require('../src/workflows/engine');
const { createTestWorkflow } = require('./helpers');
const { signQuote } = require('../src/quote');

test('generic workflow quotes require confirmation and execute idempotently', async () => {
  const counters = { executions: 0 };
  const audit = new MemoryAuditLogger();
  const engine = new WorkflowEngine({
    workflows: [createTestWorkflow('alpha', counters)],
    signingKey: 'secret',
    quoteTtlSeconds: 10,
    audit,
    nowSeconds: () => 100,
    idFactory: () => `id-${audit.records.length}`,
  });

  const quote = await engine.createQuote('alpha', { value: 'ok' });
  await assert.rejects(
    () => engine.execute('alpha', { quote_token: quote.quote_token, confirm: false }),
    error => error.code === 'confirmation_required',
  );

  const first = await engine.execute('alpha', { quote_token: quote.quote_token, confirm: true });
  const second = await engine.execute('alpha', { quote_token: quote.quote_token, confirm: true });

  assert.equal(first.idempotent_replay, false);
  assert.equal(second.idempotent_replay, true);
  assert.equal(first.execution_number, second.execution_number);
  assert.equal(counters.executions, 1);
  assert.deepEqual(audit.records.map(record => record.event), [
    'workflow.quote.created',
    'workflow.execution.started',
    'workflow.execution.completed',
    'workflow.execution.replayed',
  ]);
});

test('generic workflow rejects tampered, expired, mismatched, and structurally invalid quotes', async () => {
  let now = 100;
  const counters = { executions: 0 };
  const engine = new WorkflowEngine({
    workflows: [
      createTestWorkflow('alpha', counters),
      createTestWorkflow('beta', counters),
    ],
    signingKey: 'secret',
    quoteTtlSeconds: 10,
    nowSeconds: () => now,
    idFactory: () => 'quote-id',
  });

  const quote = await engine.createQuote('alpha', { value: 'ok' });
  await assert.rejects(
    () => engine.execute('alpha', { quote_token: `${quote.quote_token.slice(0, -1)}x`, confirm: true }),
    error => error.code === 'invalid_quote',
  );
  await assert.rejects(
    () => engine.execute('beta', { quote_token: quote.quote_token, confirm: true }),
    error => error.code === 'quote_workflow_mismatch',
  );

  now = 111;
  await assert.rejects(
    () => engine.execute('alpha', { quote_token: quote.quote_token, confirm: true }),
    error => error.code === 'invalid_quote' && /expired/i.test(error.message),
  );

  const invalidSignedQuote = signQuote({
    version: 1,
    workflow_id: 'alpha',
    quote_id: 'invalid',
    expires_at: 200,
    proposal: { value: 'changed' },
  }, 'secret');
  now = 100;
  await assert.rejects(
    () => engine.execute('alpha', { quote_token: invalidSignedQuote, confirm: true }),
    error => error.code === 'quote_not_approved',
  );
});
