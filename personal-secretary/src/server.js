const express = require('express');
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
const { getRuntimeConfig, safeEqual } = require('./config');
const { signQuote, verifyQuote } = require('./quote');
const { getAvailability, bookExactSlot } = require('./delray');

const app = express();
app.disable('x-powered-by');
app.set('trust proxy', 1);
app.use(express.json({ limit: '32kb' }));

let config;
let configurationError;
try {
  config = getRuntimeConfig();
} catch (error) {
  configurationError = error;
  console.error(`Configuration incomplete: ${error.message}`);
}

const recentRequests = new Map();
const completedBookings = new Map();
const inflightBookings = new Map();

function tokenFingerprint(token) {
  return crypto.createHash('sha256').update(String(token)).digest('hex');
}

function cleanupMaps() {
  const now = Date.now();
  for (const [key, timestamps] of recentRequests.entries()) {
    const fresh = timestamps.filter(timestamp => now - timestamp < 15 * 60_000);
    if (fresh.length) recentRequests.set(key, fresh);
    else recentRequests.delete(key);
  }
  for (const [key, record] of completedBookings.entries()) {
    if (now - record.completedAt > 24 * 60 * 60_000) completedBookings.delete(key);
  }
}
setInterval(cleanupMaps, 10 * 60_000).unref();

function requireConfigured(req, res, next) {
  if (!config) {
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
  });
});

app.get('/privacy', (req, res) => {
  res.type('text/plain').send([
    'Gurukul Personal Secretary Privacy Notice',
    '',
    'This private service uses contact details stored as deployment secrets only to complete user-requested appointments.',
    'Contact details are not returned by the API, written to the repository, or included in application logs.',
    'The service supports one approved workflow: Del Ray Barbershop, Buzzcut and Beard Trim, with Scotty.',
    'Appointment confirmations are returned without Square cancellation or rescheduling tokens.',
  ].join('\n'));
});

app.get('/openapi.yaml', (req, res) => {
  const schema = path.join(__dirname, '..', 'openapi.yaml');
  res.type('application/yaml').send(fs.readFileSync(schema, 'utf8'));
});

app.post('/v1/availability', requireConfigured, authenticate, async (req, res) => {
  try {
    const requestedWeeks = Number(req.body?.max_weeks || config.maxWeeks);
    const maxWeeks = Math.min(Math.max(Math.trunc(requestedWeeks), 1), config.maxWeeks);
    const slot = await getAvailability(config, maxWeeks);
    if (!slot) {
      return res.status(404).json({
        error: 'no_availability',
        message: `No Thursday or Friday appointment after 2:00 PM was found in the next ${maxWeeks} weeks.`,
      });
    }

    const now = Math.floor(Date.now() / 1000);
    const quotePayload = {
      version: 1,
      issued_at: now,
      expires_at: now + config.quoteTtlSeconds,
      nonce: crypto.randomUUID(),
      slot,
    };
    res.json({
      slot,
      quote_token: signQuote(quotePayload, config.signingKey),
      quote_expires_at: new Date(quotePayload.expires_at * 1000).toISOString(),
      requires_confirmation: true,
    });
  } catch (error) {
    console.error(`Availability failed: ${error.message}`);
    res.status(502).json({ error: 'availability_failed', message: error.message });
  }
});

app.post('/v1/book', requireConfigured, authenticate, async (req, res) => {
  if (req.body?.confirm !== true) {
    return res.status(400).json({
      error: 'confirmation_required',
      message: 'Set confirm to true only after the user approves the quoted appointment.',
    });
  }

  let quote;
  try {
    quote = verifyQuote(req.body?.quote_token, config.signingKey);
  } catch (error) {
    return res.status(400).json({ error: 'invalid_quote', message: error.message });
  }

  const { slot } = quote;
  const approved = slot
    && slot.business === config.businessName
    && slot.service === config.serviceName
    && slot.staff === config.staffName
    && slot.dueTodayCad === 0;
  if (!approved) {
    return res.status(400).json({ error: 'quote_not_approved' });
  }

  const fingerprint = tokenFingerprint(req.body.quote_token);
  if (completedBookings.has(fingerprint)) {
    return res.json({
      idempotent_replay: true,
      ...completedBookings.get(fingerprint).result,
    });
  }

  if (inflightBookings.has(fingerprint)) {
    try {
      const result = await inflightBookings.get(fingerprint);
      return res.json({ idempotent_replay: true, ...result });
    } catch (error) {
      return res.status(502).json({ error: 'booking_failed', message: error.message });
    }
  }

  const bookingPromise = bookExactSlot(config, {
    dateLabel: slot.dateLabel,
    timeLabel: slot.timeLabel,
  });
  inflightBookings.set(fingerprint, bookingPromise);

  try {
    const result = await bookingPromise;
    completedBookings.set(fingerprint, { result, completedAt: Date.now() });
    res.json({ idempotent_replay: false, ...result });
  } catch (error) {
    const status = error.code === 'SLOT_UNAVAILABLE' ? 409 : 502;
    console.error(`Booking failed: ${error.message}`);
    res.status(status).json({
      error: error.code === 'SLOT_UNAVAILABLE' ? 'slot_unavailable' : 'booking_failed',
      message: error.message,
    });
  } finally {
    inflightBookings.delete(fingerprint);
  }
});

app.use((req, res) => res.status(404).json({ error: 'not_found' }));

const port = Number(process.env.PORT || config?.port || 10000);
app.listen(port, '0.0.0.0', () => {
  console.log(`Gurukul Personal Secretary listening on port ${port}`);
});
