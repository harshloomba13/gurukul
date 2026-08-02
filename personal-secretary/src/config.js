const crypto = require('crypto');

const DEFAULTS = Object.freeze({
  serviceUrl: 'https://book.squareup.com/appointments/mdouxfhcb4hdk/location/M052VNBMT91HV/services/KMFJZ5DPVPEQKPVFVNN3OE6C',
  staffId: 'TMOB1VGl_XSd69SF',
  businessName: 'Del Ray Barbershop',
  serviceName: 'Buzzcut and Beard Trim',
  staffName: 'Scotty',
  locationText: '2496 Victoria Drive, Vancouver, BC',
  timezone: 'America/Vancouver',
  notBeforeMinutes: 14 * 60,
  weekdayOrder: ['Th', 'Fr'],
  // ChatGPT Actions must return before the platform request timeout. Restrict
  // both default and explicit requests to the immediate two-week window.
  defaultSearchWeeks: 2,
  maxWeeks: 2,
  quoteTtlSeconds: 10 * 60,
});

function requireEnv(name) {
  const value = process.env[name]?.trim();
  if (!value) throw new Error(`Missing required environment variable: ${name}`);
  return value;
}

function getRuntimeConfig() {
  return {
    ...DEFAULTS,
    port: Number(process.env.PORT || 10000),
    apiKey: requireEnv('SECRETARY_API_KEY'),
    signingKey: requireEnv('SECRETARY_SIGNING_KEY'),
    customer: {
      phone: requireEnv('SECRETARY_PHONE'),
      firstName: requireEnv('SECRETARY_FIRST_NAME'),
      lastName: requireEnv('SECRETARY_LAST_NAME'),
      email: requireEnv('SECRETARY_EMAIL'),
    },
  };
}

function safeEqual(left, right) {
  const a = Buffer.from(String(left || ''));
  const b = Buffer.from(String(right || ''));
  return a.length === b.length && crypto.timingSafeEqual(a, b);
}

module.exports = { DEFAULTS, getRuntimeConfig, safeEqual };
