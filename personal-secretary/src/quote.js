const crypto = require('crypto');

function encode(value) {
  return Buffer.from(JSON.stringify(value)).toString('base64url');
}

function decode(value) {
  return JSON.parse(Buffer.from(value, 'base64url').toString('utf8'));
}

function signQuote(payload, signingKey) {
  const body = encode(payload);
  const signature = crypto.createHmac('sha256', signingKey).update(body).digest('base64url');
  return `${body}.${signature}`;
}

function verifyQuote(token, signingKey, nowSeconds = Math.floor(Date.now() / 1000)) {
  const [body, suppliedSignature] = String(token || '').split('.');
  if (!body || !suppliedSignature) throw new Error('Invalid quote token');

  const expectedSignature = crypto.createHmac('sha256', signingKey).update(body).digest('base64url');
  const supplied = Buffer.from(suppliedSignature);
  const expected = Buffer.from(expectedSignature);
  if (supplied.length !== expected.length || !crypto.timingSafeEqual(supplied, expected)) {
    throw new Error('Invalid quote signature');
  }

  const payload = decode(body);
  if (!payload.expires_at || payload.expires_at < nowSeconds) throw new Error('Quote expired');
  return payload;
}

module.exports = { signQuote, verifyQuote };
