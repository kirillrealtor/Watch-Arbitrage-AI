import { chromium } from '@playwright/test';

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  
  let hasHydrationError = false;
  page.on('console', msg => {
    if (msg.type() === 'error' && msg.text().includes('Hydration failed')) {
      hasHydrationError = true;
      console.error('Found Hydration Error:', msg.text());
    }
  });
  page.on('pageerror', err => {
    if (err.message.includes('Hydration failed') || err.message.includes('hydration')) {
      hasHydrationError = true;
      console.error('Found Page Error:', err.message);
    }
  });

  console.log('Navigating to http://localhost:3000');
  await page.goto('http://localhost:3000');
  
  await page.waitForTimeout(2000);
  await browser.close();
  
  if (hasHydrationError) {
    process.exit(1);
  } else {
    console.log('No hydration errors detected!');
    process.exit(0);
  }
})();
