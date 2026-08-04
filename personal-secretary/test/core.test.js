const test = require('node:test');
const assert = require('node:assert/strict');
const { parseTimeMinutes, extractSelectedDate, normalize } = require('../src/delray');
const { signQuote, verifyQuote } = require('../src/quote');
const { safeEqual } = require('../src/config');

test('normalizes Square whitespace', () => {
  assert.equal(normalize('  2:40\u00a0 p.m.  '), '2:40 p.m.');
});

test('parses 12-hour appointment times', () => {
  assert.equal(parseTimeMinutes('2:40 p.m.'), 14 * 60 + 40);
  assert.equal(parseTimeMinutes('12:20 p.m.'), 12 * 60 + 20);
  assert.equal(parseTimeMinutes('12:20 a.m.'), 20);
  assert.equal(parseTimeMinutes('not a time'), null);
});

test('extracts the selected Square calendar date', () => {
  assert.equal(
    extractSelectedDate('Choose a time Friday, Aug 7, 2026 2:40 p.m.'),
    'Friday, Aug 7, 2026',
  );
});

test('signs, verifies, and expires booking quotes', () => {
  const token = signQuote({ expires_at: 200, slot: { dateLabel: 'Friday, Aug 7, 2026' } }, 'secret');
  assert.equal(verifyQuote(token, 'secret', 100).slot.dateLabel, 'Friday, Aug 7, 2026');
  assert.throws(() => verifyQuote(token, 'wrong', 100), /signature/);
  assert.throws(() => verifyQuote(token, 'secret', 201), /expired/);
  assert.throws(() => verifyQuote(`${token}.extra`, 'secret', 100), /Invalid quote token/);
  assert.throws(() => verifyQuote('not-json.signature', 'secret', 100), /signature|payload/);
});

test('compares API keys safely', () => {
  assert.equal(safeEqual('abc', 'abc'), true);
  assert.equal(safeEqual('abc', 'abd'), false);
  assert.equal(safeEqual('abc', 'longer'), false);
});
