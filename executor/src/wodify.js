const { chromium } = require('playwright');

class WodifyAdapter {
  constructor(config) { this.config = config; }

  validateRequest(input) {
    if (!input?.productId || !Number.isInteger(input.quantity) || input.quantity < 1) {
      throw new Error('productId and a positive integer quantity are required');
    }
  }

  async prepare(input, savedState) {
    this.validateRequest(input);
    const browser = await chromium.launch({ headless: true, args: ['--no-sandbox'] });
    try {
      const context = await browser.newContext(savedState ? { storageState: savedState } : {});
      const page = await context.newPage();
      await page.goto(this.config.storeUrl, { waitUntil: 'domcontentloaded' });
      await page.locator(`[data-product-id="${input.productId}"]`).click();
      const priceText = await page.locator('[data-testid="total-price"]').innerText();
      const total = Number(priceText.replace(/[^0-9.]/g, ''));
      if (!Number.isFinite(total)) throw new Error('Wodify did not display a valid total');
      return {
        summary: { merchant: 'CrossFit BC', productId: input.productId, quantity: input.quantity, total, currency: 'CAD' },
        state: await context.storageState(),
      };
    } finally { await browser.close(); }
  }

  async purchase() {
    // Deliberately fail closed until an operator enables and reviews real checkout selectors.
    throw new Error('Real purchase execution is disabled');
  }
}

module.exports = { WodifyAdapter };
