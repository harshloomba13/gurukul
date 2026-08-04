const test = require('node:test');
const assert = require('node:assert/strict');
const { createApp } = require('../src/server');

function routePaths(app) {
  return app.router.stack
    .filter(layer => layer.route)
    .map(layer => ({
      path: layer.route.path,
      methods: Object.keys(layer.route.methods).sort(),
    }));
}

test('server registers preserved haircut, bakery, and generic workflow routes', () => {
  const { app } = createApp({
    config: { apiKey: 'test-key', port: 0 },
    engine: {},
  });

  assert.deepEqual(routePaths(app), [
    { path: '/health', methods: ['get'] },
    { path: '/privacy', methods: ['get'] },
    { path: '/openapi.yaml', methods: ['get'] },
    { path: '/v1/availability', methods: ['post'] },
    { path: '/v1/book', methods: ['post'] },
    { path: '/v1/bakery/delivery-quote', methods: ['post'] },
    { path: '/v1/bakery/order', methods: ['post'] },
    { path: '/v1/workflows/:workflowId/quote', methods: ['post'] },
    { path: '/v1/workflows/:workflowId/execute', methods: ['post'] },
  ]);
});
