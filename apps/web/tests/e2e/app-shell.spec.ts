import { test, expect } from '@playwright/test';

test.describe('App Shell', () => {
  test('renders opportunities placeholder and shell at desktop width', async ({ page }) => {
    // Force desktop viewport
    await page.setViewportSize({ width: 1280, height: 800 });
    await page.goto('/opportunities');

    // Main content exists and has correct heading
    const mainContent = page.locator('#main-content');
    await expect(mainContent).toBeVisible();
    await expect(mainContent.locator('h1')).toHaveText('Opportunities');

    // Desktop sidebar is visible (it should have a "ChronoArb" branding text)
    // The Mobile navigation AppBar shouldn't be visible on desktop
    const sidebar = page.getByRole('navigation').filter({ hasText: 'ChronoArb' });
    await expect(sidebar).toBeVisible();
    
    // Check aria-current on the active link
    const opportunitiesLink = sidebar.getByRole('link', { name: 'Opportunities' });
    await expect(opportunitiesLink).toHaveAttribute('aria-current', 'page');
  });

  test('renders mobile shell and drawer at mobile width', async ({ page }) => {
    // Force mobile viewport
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto('/watches');

    const mainContent = page.locator('#main-content');
    await expect(mainContent).toBeVisible();
    await expect(mainContent.locator('h1')).toHaveText('Watches');

    // The open navigation button should be visible on mobile
    const menuButton = page.getByRole('button', { name: 'Open navigation' });
    await expect(menuButton).toBeVisible();

    // Drawer should initially be hidden (the list inside it isn't visible)
    const mobileLink = page.getByRole('presentation').getByRole('link', { name: 'Watches' });
    await expect(mobileLink).not.toBeVisible();

    // Open drawer
    await menuButton.click();
    await expect(mobileLink).toBeVisible();
    await expect(mobileLink).toHaveAttribute('aria-current', 'page');

    // Close via Escape
    await page.keyboard.press('Escape');
    await expect(mobileLink).not.toBeVisible();
  });

  test('drawer closes on navigation', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto('/opportunities');

    const menuButton = page.getByRole('button', { name: 'Open navigation' });
    await menuButton.click();

    // Click on Watches link inside the drawer
    const watchesLink = page.getByRole('presentation').getByRole('link', { name: 'Watches' });
    await watchesLink.click();

    // The URL should change to /watches
    await expect(page).toHaveURL('/watches');
    
    // The drawer should close
    await expect(watchesLink).not.toBeVisible();
  });

  test('skip link focuses main content', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 800 });
    await page.goto('/opportunities');

    // The skip link should be in the DOM
    const skipLink = page.getByRole('link', { name: 'Skip to main content' });
    
    // Press Tab to focus the skip link
    await page.keyboard.press('Tab');
    await expect(skipLink).toBeFocused();

    // Press Enter to activate the skip link
    await page.keyboard.press('Enter');

    // Focus should move to #main-content
    const mainContent = page.locator('#main-content');
    await expect(mainContent).toBeFocused();
  });

  const navigationDestinations = [
    { path: '/opportunities', heading: 'Opportunities' },
    { path: '/watches', heading: 'Watches' },
    { path: '/alerts', heading: 'Alerts' },
    { path: '/activity', heading: 'Activity' },
    { path: '/settings/organization', heading: 'Organization Settings' },
  ];

  for (const { path, heading } of navigationDestinations) {
    test(`navigation destination ${path} resolves successfully`, async ({ page }) => {
      const response = await page.goto(path);
      expect(response?.status()).toBe(200);
      const headingLocator = page.locator('h1');
      await expect(headingLocator).toBeVisible();
      await expect(headingLocator).toHaveText(heading);
    });
  }

  test('no horizontal overflow', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 800 });
    await page.goto('/opportunities');
    
    const bodyWidth = await page.evaluate(() => document.body.scrollWidth);
    const windowWidth = await page.evaluate(() => window.innerWidth);
    expect(bodyWidth).toBeLessThanOrEqual(windowWidth);

    await page.setViewportSize({ width: 390, height: 844 });
    const mobileBodyWidth = await page.evaluate(() => document.body.scrollWidth);
    const mobileWindowWidth = await page.evaluate(() => window.innerWidth);
    expect(mobileBodyWidth).toBeLessThanOrEqual(mobileWindowWidth);
  });
  
  test('verifies 1023px vs 1024px responsive breakpoint', async ({ page }) => {
    // 1023px: Mobile shell
    await page.setViewportSize({ width: 1023, height: 800 });
    await page.goto('/opportunities');
    const menuButton = page.getByRole('button', { name: 'Open navigation' });
    await expect(menuButton).toBeVisible();
    
    // 1024px: Desktop shell
    await page.setViewportSize({ width: 1024, height: 800 });
    await expect(menuButton).not.toBeVisible();
    const sidebar = page.getByRole('navigation').filter({ hasText: 'ChronoArb' });
    await expect(sidebar).toBeVisible();
  });
});
