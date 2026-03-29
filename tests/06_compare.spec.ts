import { test, expect } from '@playwright/test';

test.describe('06. Compare Page', () => {
  test('page loads with empty state', async ({ page }) => {
    await page.goto('/compare.html');
    await page.waitForLoadState('networkidle');
    await expect(page.locator('.text-gradient')).toBeVisible();
  });

  test('adding ETFs loads comparison table', async ({ page }) => {
    await page.goto('/compare.html');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);

    // Add SPY
    const input = page.locator('.add-input, #add-ticker-input, input[placeholder*="ticker"], input[placeholder*="ETF"]').first();
    await input.fill('SPY');
    await page.keyboard.press('Enter');
    await page.waitForTimeout(500);

    // Add QQQ
    await input.fill('QQQ');
    await page.keyboard.press('Enter');
    await page.waitForTimeout(2000);

    // Comparison table should render
    const table = page.locator('table, .compare-table, #compare-body');
    await expect(table.first()).toBeVisible({ timeout: 10000 });

    // Should contain ETF names
    const body = await page.locator('body').textContent();
    expect(body).toContain('SPY');
    expect(body).toContain('QQQ');
  });

  test('performance data loads from price history', async ({ page }) => {
    await page.goto('/compare.html');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);

    const input = page.locator('.add-input, #add-ticker-input, input[placeholder*="ticker"], input[placeholder*="ETF"]').first();
    await input.fill('SPY');
    await page.keyboard.press('Enter');
    await page.waitForTimeout(500);
    await input.fill('QQQ');
    await page.keyboard.press('Enter');
    await page.waitForTimeout(3000);

    // Check that return metrics are loaded (1Y, 3Y, 5Y)
    const body = await page.locator('body').textContent();
    // Should contain percentage values
    expect(body).toMatch(/%/);
  });
});
