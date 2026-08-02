const crypto = require('crypto');

const encode = value => Buffer.from(JSON.stringify(value)).toString('base64url');

function signQuote(payload, key) {
  const body = encode(payload);
  const signature = crypto.createHmac('sha256', key).update(body).digest('base64url');
  return `${body}.${signature}`;
}

function verifyQuote(token, key, now = Date.now()) {
  const [body, supplied] = String(token || '').split('.');
  if (!body || !supplied) throw new Error('Malformed quote token');
  const expected = crypto.createHmac('sha256', key).update(body).digest('base64url');
  const a = Buffer.from(supplied);
  const b = Buffer.from(expected);
  if (a.length !== b.length || !crypto.timingSafeEqual(a, b)) throw new Error('Invalid quote signature');
  let payload;
  try { payload = JSON.parse(Buffer.from(body, 'base64url').toString('utf8')); }
  catch { throw new Error('Malformed quote token'); }
  if (payload?.version !== 1 || typeof payload.id !== 'string' || !payload.id || !payload.summary
    || !Number.isFinite(payload.expiresAt)) throw new Error('Invalid quote payload');
  if (payload.expiresAt <= now) throw new Error('Quote expired');
  return payload;
}

module.exports = { signQuote, verifyQuote };
