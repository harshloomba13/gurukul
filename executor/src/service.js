const crypto = require('crypto');
const { signQuote, verifyQuote } = require('./quote');

class ExecutorService {
  constructor({ adapter, sessions, audit, signingKey, quoteTtlMs = 10 * 60_000 }) {
    Object.assign(this, { adapter, sessions, audit, signingKey, quoteTtlMs });
    this.results = new Map();
    this.inflight = new Map();
  }

  async prepare(input) {
    const id = crypto.randomUUID();
    const prepared = await this.adapter.prepare(input);
    await this.sessions.put(id, prepared.state);
    const payload = { version: 1, id, summary: prepared.summary, expiresAt: Date.now() + this.quoteTtlMs };
    await this.audit.record('purchase.prepared', { quoteId: id, summary: prepared.summary });
    return { quote: prepared.summary, quoteToken: signQuote(payload, this.signingKey), requiresApproval: true };
  }

  async approve({ quoteToken, approve, idempotencyKey }) {
    if (approve !== true) throw new Error('Explicit approval is required');
    if (!idempotencyKey) throw new Error('Idempotency-Key is required');
    const quote = verifyQuote(quoteToken, this.signingKey);
    const key = crypto.createHash('sha256').update(idempotencyKey).digest('hex');
    const completed = this.results.get(key);
    if (completed) {
      if (completed.quoteId !== quote.id) throw new Error('Idempotency-Key was already used for another quote');
      return { ...completed.result, idempotentReplay: true };
    }
    const pending = this.inflight.get(key);
    if (pending) {
      if (pending.quoteId !== quote.id) throw new Error('Idempotency-Key is already in use for another quote');
      return { ...(await pending.operation), idempotentReplay: true };
    }
    const operation = (async () => {
      const state = await this.sessions.get(quote.id);
      await this.audit.record('purchase.approved', { quoteId: quote.id, idempotencyHash: key });
      return this.adapter.purchase(quote, state);
    })();
    this.inflight.set(key, { quoteId: quote.id, operation });
    try {
      const result = await operation;
      this.results.set(key, { quoteId: quote.id, result });
      await this.audit.record('purchase.completed', { quoteId: quote.id, idempotencyHash: key });
      return { ...result, idempotentReplay: false };
    } finally { this.inflight.delete(key); }
  }
}

module.exports = { ExecutorService };
