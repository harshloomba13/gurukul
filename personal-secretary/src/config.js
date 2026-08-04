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
  bakery: {
    merchant: {
      id: 'sandbox-bakery',
      name: 'Sandbox Bakery',
    },
    products: [
      {
        sku: 'sourdough-loaf',
        name: 'Country Sourdough Loaf',
        unitPriceCad: 8.5,
        maxQuantity: 4,
      },
      {
        sku: 'croissant-box-6',
        name: 'Butter Croissant Box',
        unitPriceCad: 21,
        maxQuantity: 2,
      },
      {
        sku: 'cinnamon-roll-box-4',
        name: 'Cinnamon Roll Box',
        unitPriceCad: 18,
        maxQuantity: 3,
      },
    ],
    deliveryDestinationRefs: ['home', 'office'],
    deliveryWindows: [
      { id: 'asap', label: 'Next available sandbox delivery window' },
      { id: 'today_4_6_pm', label: 'Today, 4:00 PM-6:00 PM' },
      { id: 'tomorrow_9_11_am', label: 'Tomorrow, 9:00 AM-11:00 AM' },
    ],
    defaultDeliveryWindow: 'asap',
    deliveryFeeCad: 6.5,
    taxRate: 0.05,
    maxTotalQuantity: 6,
    spendingLimitCad: 75,
    tip: {
      enabled: true,
      maxCad: 10,
    },
  },
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
