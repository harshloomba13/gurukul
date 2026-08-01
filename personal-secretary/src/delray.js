const { chromium } = require('playwright');

const normalize = value => String(value || '')
  .replace(/\u00a0/g, ' ')
  .replace(/\s+/g, ' ')
  .trim();

function parseTimeMinutes(text) {
  const match = normalize(text).toLowerCase().match(/(\d{1,2}):(\d{2})\s*([ap])\.?m\.?/);
  if (!match) return null;
  let hour = Number(match[1]);
  const minute = Number(match[2]);
  if (match[3] === 'p' && hour !== 12) hour += 12;
  if (match[3] === 'a' && hour === 12) hour = 0;
  return hour * 60 + minute;
}

function extractSelectedDate(bodyText) {
  const pattern = /(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},\s+\d{4}/;
  return normalize(bodyText).match(pattern)?.[0] || null;
}

async function openAvailability(page, config) {
  await page.goto(config.serviceUrl, { waitUntil: 'domcontentloaded', timeout: 60_000 });
  await page.waitForTimeout(4_000);

  const staff = page.locator(`market-row[role="option"][value="${config.staffId}"]`);
  await staff.waitFor({ state: 'visible', timeout: 20_000 });
  await staff.click();

  const bookButtons = page.locator('market-button').filter({ hasText: /^Book$/ });
  await bookButtons.last().click();
  await page.waitForURL(/\/availability/, { timeout: 30_000 });
  await page.waitForTimeout(3_000);
}

async function visibleDateCandidates(page, config) {
  const buttons = page.locator('market-button:visible');
  const snapshot = await buttons.evaluateAll(elements => elements.map((element, index) => ({
    index,
    text: (element.innerText || element.textContent || '')
      .replace(/\u00a0/g, ' ')
      .replace(/\s+/g, ' ')
      .trim(),
    disabled: Boolean(element.disabled) || element.hasAttribute('disabled'),
  })));

  return snapshot
    .filter(item => /^(Th|Fr)\s+\d+$/.test(item.text) && !item.disabled)
    .sort((left, right) => {
      const leftDay = config.weekdayOrder.indexOf(left.text.slice(0, 2));
      const rightDay = config.weekdayOrder.indexOf(right.text.slice(0, 2));
      return leftDay - rightDay || left.index - right.index;
    });
}

async function readEligibleTimes(page, config) {
  const timeButtons = page.locator('market-button[role="listitem"]:visible');
  const labels = (await timeButtons.allTextContents()).map(normalize);
  return labels
    .map((label, index) => ({ label, index, minutes: parseTimeMinutes(label) }))
    .filter(slot => slot.minutes !== null && slot.minutes >= config.notBeforeMinutes);
}

async function moveToNextWeek(page) {
  const next = page.locator('button[aria-label="Next week"]:visible').first();
  if (!(await next.count()) || await next.isDisabled().catch(() => true)) return false;
  await next.click();
  await page.waitForTimeout(1_700);
  return true;
}

async function findFirstEligibleSlot(page, config, maxWeeks = config.maxWeeks) {
  for (let week = 0; week < maxWeeks; week += 1) {
    const candidates = await visibleDateCandidates(page, config);

    for (const candidate of candidates) {
      const currentButtons = page.locator('market-button:visible');
      if (candidate.index >= await currentButtons.count()) continue;
      const button = currentButtons.nth(candidate.index);
      if (normalize(await button.innerText().catch(() => '')) !== candidate.text) continue;
      if (await button.isDisabled().catch(() => true)) continue;

      await button.click();
      await page.waitForTimeout(1_400);
      const dateLabel = extractSelectedDate(await page.locator('body').innerText());
      const times = await readEligibleTimes(page, config);
      if (dateLabel && times.length) {
        return { dateLabel, timeLabel: times[0].label, week };
      }
    }

    if (!(await moveToNextWeek(page))) break;
  }
  return null;
}

async function selectExactSlot(page, config, target, maxWeeks = config.maxWeeks) {
  for (let week = 0; week < maxWeeks; week += 1) {
    const candidates = await visibleDateCandidates(page, config);

    for (const candidate of candidates) {
      const currentButtons = page.locator('market-button:visible');
      if (candidate.index >= await currentButtons.count()) continue;
      const button = currentButtons.nth(candidate.index);
      if (normalize(await button.innerText().catch(() => '')) !== candidate.text) continue;
      if (await button.isDisabled().catch(() => true)) continue;

      await button.click();
      await page.waitForTimeout(1_400);
      const dateLabel = extractSelectedDate(await page.locator('body').innerText());
      if (dateLabel !== target.dateLabel) continue;

      const timeButtons = page.locator('market-button[role="listitem"]:visible');
      const labels = (await timeButtons.allTextContents()).map(normalize);
      const index = labels.findIndex(label => label === target.timeLabel);
      if (index < 0) return false;

      await timeButtons.nth(index).click();
      await page.waitForURL(/\/checkout/, { timeout: 30_000 });
      await page.waitForTimeout(3_000);
      return true;
    }

    if (!(await moveToNextWeek(page))) break;
  }
  return false;
}

async function withPage(config, operation) {
  const browser = await chromium.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-dev-shm-usage'],
  });
  try {
    const context = await browser.newContext({
      viewport: { width: 1440, height: 1200 },
      locale: 'en-CA',
      timezoneId: config.timezone,
    });
    const page = await context.newPage();
    page.setDefaultTimeout(12_000);
    return await operation(page);
  } finally {
    await browser.close();
  }
}

async function getAvailability(config, maxWeeks) {
  return withPage(config, async page => {
    await openAvailability(page, config);
    const slot = await findFirstEligibleSlot(page, config, maxWeeks);
    if (!slot) return null;
    return {
      ...slot,
      business: config.businessName,
      service: config.serviceName,
      staff: config.staffName,
      location: config.locationText,
      estimatedPriceCad: 36,
      dueTodayCad: 0,
    };
  });
}

function verifyCheckout(text, config, target) {
  const checkout = normalize(text);
  const required = [
    config.businessName,
    config.serviceName,
    `with ${config.staffName}`,
    'Due today $0.00',
  ];
  for (const phrase of required) {
    if (!checkout.includes(phrase)) throw new Error(`Checkout verification failed: ${phrase}`);
  }

  const dateWithoutYear = target.dateLabel.replace(/,\s*\d{4}$/, '');
  const startTime = target.timeLabel.match(/\d{1,2}:\d{2}/)?.[0];
  if (!checkout.includes(dateWithoutYear) || !startTime || !checkout.includes(startTime)) {
    throw new Error('Checkout date/time differs from the signed quote');
  }
}

function sanitizeConfirmation(text, target, config) {
  const confirmation = normalize(text);
  return {
    business: config.businessName,
    service: config.serviceName,
    staff: config.staffName,
    date: target.dateLabel,
    time: target.timeLabel,
    location: config.locationText,
    estimatedDueAtAppointmentCad: 36,
    confirmed: /thanks for booking|appointment (?:is )?(?:confirmed|booked)|you(?:'|’)re (?:all )?set/i.test(confirmation),
  };
}

async function bookExactSlot(config, target) {
  return withPage(config, async page => {
    await openAvailability(page, config);
    const selected = await selectExactSlot(page, config, target);
    if (!selected) {
      const error = new Error('The quoted slot is no longer available');
      error.code = 'SLOT_UNAVAILABLE';
      throw error;
    }

    verifyCheckout(await page.locator('body').innerText(), config, target);
    await page.locator('input[name="phone"]').fill(config.customer.phone);
    await page.locator('input[name="firstName"]').fill(config.customer.firstName);
    await page.locator('input[name="lastName"]').fill(config.customer.lastName);
    await page.locator('input[name="email"]').fill(config.customer.email);

    const submit = page.getByTestId('book-appointment-button-desktop');
    if (await submit.count()) {
      await submit.click();
    } else {
      await page.locator('market-button[type="submit"]:visible').filter({ hasText: /Book appointment/i }).first().click();
    }

    await Promise.race([
      page.waitForURL(/\/confirmation|\/success/, { timeout: 30_000 }),
      page.getByText(/Thanks for booking/i).waitFor({ state: 'visible', timeout: 30_000 }),
    ]).catch(() => {});
    await page.waitForTimeout(2_000);

    const result = sanitizeConfirmation(await page.locator('body').innerText(), target, config);
    if (!result.confirmed && !/\/confirmation|\/success/.test(page.url())) {
      throw new Error('Square did not return a recognizable confirmation');
    }
    result.confirmed = true;
    return result;
  });
}

module.exports = {
  normalize,
  parseTimeMinutes,
  extractSelectedDate,
  getAvailability,
  bookExactSlot,
};
