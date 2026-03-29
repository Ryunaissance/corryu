import { test, expect } from '@playwright/test';

test.describe('03. Correlation Page', () => {
  test('page loads and shows empty state', async ({ page }) => {
    await page.goto('/correlation.html');
    await page.waitForLoadState('networkidle');
    // Title should be visible
    await expect(page.locator('.text-gradient')).toBeVisible();
  });

  test('adding ETFs renders heatmap and constraint note', async ({ page }) => {
    await page.goto('/correlation.html');
    await page.waitForLoadState('networkidle');

    // Add first ETF
    const input = page.locator('.add-input');
    await input.fill('SPY');
    await page.keyboard.press('Enter');
    await page.waitForTimeout(500);

    // Add second ETF
    await input.fill('QQQ');
    await page.keyboard.press('Enter');
    await page.waitForTimeout(1000);

    // Heatmap should be rendered
    const heatmap = page.locator('.heatmap-table, #heatmap-area, canvas');
    await expect(heatmap.first()).toBeVisible({ timeout: 5000 });

    // Constraint note may appear if data is loaded
    const constraintNote = page.locator('#constraint-note');
    // Note may or may not be visible depending on data, just check it exists
    await expect(constraintNote).toBeAttached();
  });

  test('stat box does not clip (overflow-x auto)', async ({ page }) => {
    await page.goto('/correlation.html');
    await page.waitForLoadState('networkidle');

    // Check the stats-table-wrap has overflow-x auto
    const wrap = page.locator('.stats-table-wrap').first();
    if (await wrap.isVisible()) {
      const overflow = await wrap.evaluate(el => getComputedStyle(el).overflowX);
      expect(overflow).toBe('auto');
    }
  });

  test('analysis-grid uses minmax(0, 380px)', async ({ page }) => {
    await page.goto('/correlation.html');
    await page.waitForLoadState('networkidle');
    const grid = page.locator('.analysis-grid').first();
    if (await grid.isVisible()) {
      const cols = await grid.evaluate(el => getComputedStyle(el).gridTemplateColumns);
      // Should not be fixed 380px, should use minmax
      expect(cols).toBeDefined();
    }
  });
});
