const crypto = require('crypto');
const { signQuote, verifyQuote } = require('../quote');
const { WorkflowError } = require('./errors');

function tokenFingerprint(token) {
  return crypto.createHash('sha256').update(String(token)).digest('hex');
}

class WorkflowEngine {
  constructor({
    workflows,
    signingKey,
    quoteTtlSeconds,
    audit,
    nowSeconds = () => Math.floor(Date.now() / 1000),
    idFactory = () => crypto.randomUUID(),
    completedTtlMs = 24 * 60 * 60_000,
  }) {
    if (!signingKey) throw new Error('WorkflowEngine requires a signing key');
    this.signingKey = signingKey;
    this.quoteTtlSeconds = quoteTtlSeconds;
    this.audit = audit || { record: async () => {} };
    this.nowSeconds = nowSeconds;
    this.idFactory = idFactory;
    this.completedTtlMs = completedTtlMs;
    this.workflows = new Map((workflows || []).map(workflow => [workflow.id, workflow]));
    this.completedExecutions = new Map();
    this.inflightExecutions = new Map();
  }

  getWorkflow(workflowId) {
    const workflow = this.workflows.get(workflowId);
    if (!workflow) {
      throw new WorkflowError('unknown_workflow', `Unknown workflow: ${workflowId}`, 404);
    }
    return workflow;
  }

  cleanup() {
    const now = Date.now();
    for (const [fingerprint, record] of this.completedExecutions.entries()) {
      if (now - record.completedAt > this.completedTtlMs) {
        this.completedExecutions.delete(fingerprint);
      }
    }
  }

  async createQuote(workflowId, input = {}) {
    this.cleanup();
    const workflow = this.getWorkflow(workflowId);
    let proposal;
    try {
      proposal = await workflow.createProposal(input);
    } catch (error) {
      if (error instanceof WorkflowError) throw error;
      throw new WorkflowError(workflow.quoteFailedCode || 'quote_failed', error.message, 502);
    }
    if (workflow.validateProposal) workflow.validateProposal(proposal);

    const issuedAt = this.nowSeconds();
    const ttlSeconds = workflow.quoteTtlSeconds || this.quoteTtlSeconds;
    const basePayload = {
      version: 1,
      workflow_id: workflow.id,
      quote_id: this.idFactory(),
      issued_at: issuedAt,
      expires_at: issuedAt + ttlSeconds,
      nonce: this.idFactory(),
    };
    const payload = workflow.toQuotePayload
      ? workflow.toQuotePayload(basePayload, proposal)
      : { ...basePayload, proposal };
    const quoteToken = signQuote(payload, this.signingKey);
    const quoteExpiresAt = new Date(payload.expires_at * 1000).toISOString();

    await this.audit.record('workflow.quote.created', {
      workflow_id: workflow.id,
      quote_id: payload.quote_id,
      proposal: workflow.auditProposal ? workflow.auditProposal(proposal) : proposal,
    });

    return workflow.formatQuoteResponse({
      proposal,
      quoteToken,
      quoteExpiresAt,
      quotePayload: payload,
    });
  }

  readQuoteForWorkflow(workflowId, quoteToken) {
    const workflow = this.getWorkflow(workflowId);
    let quotePayload;
    try {
      quotePayload = verifyQuote(quoteToken, this.signingKey, this.nowSeconds());
    } catch (error) {
      throw new WorkflowError('invalid_quote', error.message, 400);
    }

    if (quotePayload.workflow_id && quotePayload.workflow_id !== workflow.id) {
      throw new WorkflowError('quote_workflow_mismatch', 'Quote token was not issued for this workflow.', 400);
    }
    if (!quotePayload.workflow_id && !workflow.acceptsLegacyQuote) {
      throw new WorkflowError('quote_workflow_mismatch', 'Quote token was not issued for this workflow.', 400);
    }

    const proposal = workflow.fromQuotePayload
      ? workflow.fromQuotePayload(quotePayload)
      : quotePayload.proposal;
    if (!proposal) {
      throw new WorkflowError('invalid_quote', 'Quote token is missing a workflow proposal.', 400);
    }
    if (workflow.validateProposal) workflow.validateProposal(proposal, quotePayload);

    return { workflow, quotePayload, proposal };
  }

  async execute(workflowId, { quote_token: quoteToken, confirm }) {
    this.cleanup();
    if (confirm !== true) {
      throw new WorkflowError(
        'confirmation_required',
        'Set confirm to true only after the user approves the quoted action.',
        400,
      );
    }

    const { workflow, quotePayload, proposal } = this.readQuoteForWorkflow(workflowId, quoteToken);
    const fingerprint = tokenFingerprint(quoteToken);

    if (this.completedExecutions.has(fingerprint)) {
      await this.audit.record('workflow.execution.replayed', {
        workflow_id: workflow.id,
        quote_id: quotePayload.quote_id,
      });
      return {
        idempotent_replay: true,
        ...this.completedExecutions.get(fingerprint).result,
      };
    }

    if (this.inflightExecutions.has(fingerprint)) {
      const result = await this.inflightExecutions.get(fingerprint);
      return { idempotent_replay: true, ...result };
    }

    const operation = (async () => {
      try {
        await this.audit.record('workflow.execution.started', {
          workflow_id: workflow.id,
          quote_id: quotePayload.quote_id,
        });
        return await workflow.execute(proposal, quotePayload);
      } catch (error) {
        const mapped = workflow.mapExecutionError ? workflow.mapExecutionError(error) : error;
        if (mapped instanceof WorkflowError) throw mapped;
        throw new WorkflowError(workflow.executionFailedCode || 'execution_failed', mapped.message, 502);
      }
    })();
    this.inflightExecutions.set(fingerprint, operation);

    try {
      const result = await operation;
      this.completedExecutions.set(fingerprint, { result, completedAt: Date.now() });
      await this.audit.record('workflow.execution.completed', {
        workflow_id: workflow.id,
        quote_id: quotePayload.quote_id,
      });
      return { idempotent_replay: false, ...result };
    } finally {
      this.inflightExecutions.delete(fingerprint);
    }
  }
}

module.exports = { WorkflowEngine, WorkflowError, tokenFingerprint };
