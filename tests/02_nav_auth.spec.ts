import { test, expect } from '@playwright/test';

const PAGES = [
  { path: '/index.html',       name: 'Dashboard' },
  { path: '/screener.html',    name: 'Screener' },
  { path: '/backtest.html',    name: 'Backtest' },
  { path: '/correlation.html', name: 'Correlation' },
  { path: '/compare.html',     name: 'Compare' },
  { path: '/portfolio.html',   name: 'Portfolio' },
  { path: '/graph.html',       name: 'Graph' },
];

test.describe('02. Nav & Auth across all pages', () => {
  for (const pg of PAGES) {
    test(`${pg.name}: login button visible`, async ({ page }) => {
      await page.goto(pg.path);
      await page.waitForLoadState('networkidle');
      // nav.js renderAuth should show login button when not logged in
      const loginBtn = page.locator('#nav-login-btn, #nav-mob-login-btn');
      // At least one login button should exist (desktop or mobile)
      await expect(loginBtn.first()).toBeVisible({ timeout: 5000 });
    });
  }

  test('Theme toggle works on dashboard', async ({ page }) => {
    await page.goto('/index.html');
    await page.waitForLoadState('networkidle');
    // Default should be dark (no data-theme attribute)
    const html = page.locator('html');
    const initialTheme = await html.getAttribute('data-theme');
    // Click theme toggle
    const toggle = page.locator('.theme-toggle').first();
    await toggle.click();
    await page.waitForTimeout(300);
    const newTheme = await html.getAttribute('data-theme');
    expect(newTheme !== initialTheme).toBeTruthy();
  });

  test('Mobile viewport: hamburger menu works', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto('/screener.html');
    await page.waitForLoadState('networkidle');
    // Hamburger button should be visible
    const hamburger = page.locator('#nav-mob-btn');
    await expect(hamburger).toBeVisible();
    // Click to open drawer
    await hamburger.click();
    const drawer = page.locator('#nav-mob-drawer');
    await expect(drawer).toHaveClass(/open/);
  });

  test('Mobile viewport: dashboard renders', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto('/index.html');
    await page.waitForLoadState('networkidle');
    await expect(page.locator('.text-gradient')).toContainText('Master Valuation');
  });
});
