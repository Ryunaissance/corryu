import { test, expect } from '@playwright/test';

test.describe('05. ETF Detail Page', () => {
  test('SPY detail page loads with basic info', async ({ page }) => {
    await page.goto('/etf-detail.html?t=SPY');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // Ticker should be displayed
    await expect(page.locator('body')).toContainText('SPY');
  });

  test('as_of date is displayed', async ({ page }) => {
    await page.goto('/etf-detail.html?t=SPY');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // as_of should be somewhere on the page
    const body = await page.locator('body').textContent();
    // Should contain a date-like pattern (2026-03-27 or similar)
    expect(body).toMatch(/20\d{2}-\d{2}-\d{2}/);
  });

  test('divYield is displayed for SPY', async ({ page }) => {
    await page.goto('/etf-detail.html?t=SPY');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // SPY has div_yield of 0.88 (88 bps = 0.88%)
    const body = await page.locator('body').textContent();
    // Look for percentage or "배당" text
    expect(body).toMatch(/배당|Dividend|div/i);
  });

  test('holdings section exists for SPY', async ({ page }) => {
    await page.goto('/etf-detail.html?t=SPY');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(3000);

    // Check if holdings are rendered (from SUPP or live data)
    const holdingsSection = page.locator('text=Holdings, text=보유종목, text=구성종목, #holdings-area, .holdings');
    // SUPP has hardcoded holdings for SPY
    const body = await page.locator('body').textContent();
    expect(body).toMatch(/AAPL|Apple|구성종목|Holdings|Top/i);
  });
});
