const express = require('express');
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
const { ConsoleAuditLogger } = require('./audit');
const { getRuntimeConfig, safeEqual } = require('./config');
const { WorkflowEngine, WorkflowError, tokenFingerprint } = require('./workflows/engine');
const { createHaircutWorkflow } = require('./workflows/haircut');
const { FakeBakeryProvider } = require('./bakery/fake-provider');
const { createBakeryWorkflow } = require('./bakery/workflow');
const { VjFlowerSubscriptionProvider } = require('./flowers/provider');
const { createFlowerSubscriptionWorkflow } = require('./flowers/workflow');

function createWorkflowEngine(config, audit = new ConsoleAuditLogger()) {
  return new WorkflowEngine({
    workflows: [
      createHaircutWorkflow({ config }),
      createBakeryWorkflow({
        config: config.bakery,
        provider: new FakeBakeryProvider(),
      }),
      createFlowerSubscriptionWorkflow({
        config: config.flowers,
        provider: new VjFlowerSubscriptionProvider(),
      }),
    ],
    signingKey: config.signingKey,
    quoteTtlSeconds: config.quoteTtlSeconds,
    audit,
  });
}

function sendWorkflowError(res, error, fallbackCode = 'request_failed') {
  if (error instanceof WorkflowError) {
    if (error.code === 'quote_not_approved') return res.status(error.status).json({ error: error.code });
    return res.status(error.status).json({ error: error.code, message: error.message });
  }
  console.error(`${fallbackCode}: ${error.stack || error.message}`);
  return res.status(500).json({ error: fallbackCode, message: 'Unexpected service error.' });
}

function createApp(options = {}) {
  const app = express();
  app.disable('x-powered-by');
  app.set('trust proxy', 1);
  app.use(express.json({ limit: '32kb' }));

  let { config, configurationError, engine, audit } = options;
  audit = audit || new ConsoleAuditLogger();
  if (!config && !configurationError) {
    try {
      config = getRuntimeConfig();
    } catch (error) {
      configurationError = error;
      console.error(`Configuration incomplete: ${error.message}`);
    }
  }
  if (config && !engine) engine = createWorkflowEngine(config, audit);

  const recentRequests = new Map();

  function cleanupRateLimits() {
    const now = Date.now();
    for (const [key, timestamps] of recentRequests.entries()) {
      const fresh = timestamps.filter(timestamp => now - timestamp < 15 * 60_000);
      if (fresh.length) recentRequests.set(key, fresh);
      else recentRequests.delete(key);
    }
  }
  const cleanupTimer = setInterval(cleanupRateLimits, 10 * 60_000);
  cleanupTimer.unref();

  app.use((req, res, next) => {
    const startedAt = Date.now();
    const requestId = crypto.randomUUID().slice(0, 8);
    console.log(`[${requestId}] ${req.method} ${req.path} started`);
    res.on('finish', () => {
      console.log(`[${requestId}] ${req.method} ${req.path} ${res.statusCode} in ${Date.now() - startedAt}ms`);
    });
    next();
  });

  function requireConfigured(req, res, next) {
    if (!config || !engine) {
      return res.status(503).json({
        error: 'service_not_configured',
        message: configurationError?.message || 'Required environment variables are missing.',
      });
    }
    next();
  }

  function authenticate(req, res, next) {
    const supplied = req.get('x-secretary-key');
    if (!supplied || !safeEqual(supplied, config.apiKey)) {
      return res.status(401).json({ error: 'unauthorized' });
    }

    const key = tokenFingerprint(supplied);
    const now = Date.now();
    const timestamps = (recentRequests.get(key) || []).filter(timestamp => now - timestamp < 15 * 60_000);
    if (timestamps.length >= 20) {
      return res.status(429).json({ error: 'rate_limited', retry_after_seconds: 900 });
    }
    timestamps.push(now);
    recentRequests.set(key, timestamps);
    next();
  }

  app.get('/health', (req, res) => {
    res.json({
      status: 'ok',
      configured: Boolean(config),
      service: 'gurukul-personal-secretary',
      workflows: config ? ['haircut', 'bakery_delivery', 'flower_subscription'] : [],
    });
  });

  app.get('/privacy', (req, res) => {
    res.type('text/plain').send([
      'Gurukul Personal Secretary Privacy Notice',
      '',
      'This private service uses contact details stored as deployment secrets only to complete user-requested appointments.',
      'Contact details are not returned by the API, written to the repository, or included in application logs.',
      'The service supports approved quote-and-confirm workflows for the Del Ray Barbershop haircut, sandbox bakery delivery, and V&J monthly floral subscription checkout.',
      'Appointment confirmations are returned without Square cancellation or rescheduling tokens.',
      'Bakery delivery uses a deterministic fake provider in this version and cannot place a real order or charge payment.',
      'The flower workflow checks the florist public catalog and returns a checkout handoff. It does not collect addresses, payment data, place an order, or create a subscription.',
    ].join('\n'));
  });

  app.get('/openapi.yaml', (req, res) => {
    const schema = path.join(__dirname, '..', 'openapi.yaml');
    res.type('application/yaml').send(fs.readFileSync(schema, 'utf8'));
  });

  app.post('/v1/availability', requireConfigured, authenticate, async (req, res) => {
    try {
      res.json(await engine.createQuote('haircut', req.body || {}));
    } catch (error) {
      if (error instanceof WorkflowError) {
        return res.status(error.status).json({ error: error.code, message: error.message });
      }
      console.error(`Availability failed: ${error.stack || error.message}`);
      res.status(502).json({ error: 'availability_failed', message: error.message });
    }
  });

  app.post('/v1/book', requireConfigured, authenticate, async (req, res) => {
    try {
      res.json(await engine.execute('haircut', {
        quote_token: req.body?.quote_token,
        confirm: req.body?.confirm,
      }));
    } catch (error) {
      if (error.code === 'confirmation_required') {
        return res.status(400).json({
          error: 'confirmation_required',
          message: 'Set confirm to true only after the user approves the quoted appointment.',
        });
      }
      return sendWorkflowError(res, error, 'booking_failed');
    }
  });

  app.post('/v1/bakery/delivery-quote', requireConfigured, authenticate, async (req, res) => {
    try {
      res.json(await engine.createQuote('bakery_delivery', req.body || {}));
    } catch (error) {
      return sendWorkflowError(res, error, 'bakery_quote_failed');
    }
  });

  app.post('/v1/bakery/order', requireConfigured, authenticate, async (req, res) => {
    try {
      res.json(await engine.execute('bakery_delivery', {
        quote_token: req.body?.quote_token,
        confirm: req.body?.confirm,
      }));
    } catch (error) {
      return sendWorkflowError(res, error, 'bakery_order_failed');
    }
  });

  app.post('/v1/flowers/subscription-quote', requireConfigured, authenticate, async (req, res) => {
    try {
      res.json(await engine.createQuote('flower_subscription', req.body || {}));
    } catch (error) {
      return sendWorkflowError(res, error, 'flower_quote_failed');
    }
  });

  app.post('/v1/flowers/prepare-checkout', requireConfigured, authenticate, async (req, res) => {
    try {
      res.json(await engine.execute('flower_subscription', {
        quote_token: req.body?.quote_token,
        confirm: req.body?.confirm,
      }));
    } catch (error) {
      return sendWorkflowError(res, error, 'flower_checkout_failed');
    }
  });

  app.post('/v1/workflows/:workflowId/quote', requireConfigured, authenticate, async (req, res) => {
    try {
      res.json(await engine.createQuote(req.params.workflowId, req.body || {}));
    } catch (error) {
      return sendWorkflowError(res, error, 'workflow_quote_failed');
    }
  });

  app.post('/v1/workflows/:workflowId/execute', requireConfigured, authenticate, async (req, res) => {
    try {
      res.json(await engine.execute(req.params.workflowId, {
        quote_token: req.body?.quote_token,
        confirm: req.body?.confirm,
      }));
    } catch (error) {
      return sendWorkflowError(res, error, 'workflow_execution_failed');
    }
  });

  app.use((req, res) => res.status(404).json({ error: 'not_found' }));
  return { app, config, engine };
}

function start() {
  const { app, config } = createApp();
  const port = Number(process.env.PORT || config?.port || 10000);
  app.listen(port, '0.0.0.0', () => {
    console.log(`Gurukul Personal Secretary listening on port ${port}`);
  });
}

if (require.main === module) start();

module.exports = { createApp, createWorkflowEngine };
