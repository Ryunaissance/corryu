import { test, expect } from '@playwright/test';

test.describe('04. Backtest Page', () => {
  test('page loads with preset buttons', async ({ page }) => {
    await page.goto('/backtest.html');
    await page.waitForLoadState('networkidle');
    // Page title should be visible
    await expect(page.locator('.page-title')).toBeVisible();
    // Should have portfolio row inputs
    await expect(page.locator('.port-row').first()).toBeVisible({ timeout: 5000 });
  });

  test('adding ETF and running backtest shows results', async ({ page }) => {
    await page.goto('/backtest.html');
    await page.waitForLoadState('networkidle');

    // Wait for data to load
    await page.waitForTimeout(2000);

    // Fill first row with SPY 60%
    const tickerInputs = page.locator('.ticker-inp');
    const weightInputs = page.locator('.weight-inp');
    await tickerInputs.first().fill('SPY');
    await tickerInputs.first().press('Tab');
    await weightInputs.first().fill('60');

    // Add BND 40%
    const addBtn = page.locator('#add-row-btn');
    await addBtn.click();
    await page.waitForTimeout(300);
    await tickerInputs.nth(1).fill('BND');
    await tickerInputs.nth(1).press('Tab');
    await weightInputs.nth(1).fill('40');

    // Click run
    const runBtn = page.locator('#run-btn, button:has-text("Run"), button:has-text("실행")');
    await runBtn.first().click();
    await page.waitForTimeout(2000);

    // Results area should be visible
    const results = page.locator('#result-area, .stat-cards, #bt-chart');
    await expect(results.first()).toBeVisible({ timeout: 10000 });
  });

  test('constraint note renders when ETF has limited history', async ({ page }) => {
    await page.goto('/backtest.html');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // Use IBIT (first year 2025) to trigger constraint with 10yr period
    const tickerInputs = page.locator('.ticker-inp');
    const weightInputs = page.locator('.weight-inp');
    await tickerInputs.first().fill('SPY');
    await tickerInputs.first().press('Tab');
    await weightInputs.first().fill('50');

    const addBtn = page.locator('#add-row-btn');
    await addBtn.click();
    await page.waitForTimeout(300);
    // Use IBIT which only has 2025 data
    await tickerInputs.nth(1).fill('IBIT');
    await tickerInputs.nth(1).press('Tab');
    await weightInputs.nth(1).fill('50');

    // Set period to 10 years to ensure constraint triggers
    const tab10 = page.locator('.sg-tab[data-yr="10"]');
    await tab10.click();

    const runBtn = page.locator('#run-btn, button:has-text("Run"), button:has-text("실행")');
    await runBtn.first().click();
    await page.waitForTimeout(3000);

    // Constraint note should appear
    const note = page.locator('#bt-constraint-note');
    await expect(note).toBeVisible({ timeout: 5000 });
    const text = await note.textContent();
    expect(text).toContain('constrained');
  });
});
