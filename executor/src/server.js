const express = require('express');
const crypto = require('crypto');
const { ExecutorService } = require('./service');
const { WodifyAdapter } = require('./wodify');
const { EncryptedSessionStore } = require('./session-store');
const { AuditLog } = require('./audit');

const required = name => process.env[name] || (() => { throw new Error(`Missing ${name}`); })();
const safeEqual = (a, b) => { const x = Buffer.from(a || ''); const y = Buffer.from(b || ''); return x.length === y.length && crypto.timingSafeEqual(x, y); };
const app = express();
app.disable('x-powered-by');
app.use(express.json({ limit: '32kb' }));
let service;
let startupError;
try {
  service = new ExecutorService({
    adapter: new WodifyAdapter({ storeUrl: required('WODIFY_STORE_URL') }),
    sessions: new EncryptedSessionStore(process.env.SESSION_DIR || '/var/data/sessions', required('SESSION_ENCRYPTION_KEY')),
    audit: new AuditLog(process.env.AUDIT_LOG || '/var/data/audit/events.jsonl'),
    signingKey: required('QUOTE_SIGNING_KEY'),
  });
} catch (error) { startupError = error; }
const auth = (req, res, next) => process.env.EXECUTOR_API_KEY
  && safeEqual(req.get('authorization'), `Bearer ${process.env.EXECUTOR_API_KEY}`)
  ? next()
  : res.status(401).json({ error: 'unauthorized' });
const ready = (req, res, next) => service ? next() : res.status(503).json({ error: 'not_configured' });
app.get('/health', (req, res) => res.status(service ? 200 : 503).json({ status: service ? 'ok' : 'not_configured', detail: startupError?.message }));
app.post('/v1/purchases/prepare', auth, ready, async (req, res) => { try { res.json(await service.prepare(req.body)); } catch (e) { res.status(400).json({ error: e.message }); } });
app.post('/v1/purchases/approve', auth, ready, async (req, res) => { try { res.json(await service.approve({ ...req.body, idempotencyKey: req.get('idempotency-key') })); } catch (e) { res.status(409).json({ error: e.message }); } });
app.listen(Number(process.env.PORT || 10000), '0.0.0.0');
