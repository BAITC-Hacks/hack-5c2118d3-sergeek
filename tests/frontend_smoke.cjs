// Run against docker compose. PLAYWRIGHT_MODULE can point to a shared runtime.
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const assert = require('node:assert/strict');

(async () => {
  const browser = await chromium.launch({ headless: true, channel: 'msedge' });
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
    const errors = [];
    const preset = await page.request.post('http://localhost:5173/api/simulations/run', {
      data: { runs: 10, seed_start: 10 },
    });
    assert.equal(preset.status(), 200);
    page.on('pageerror', error => errors.push(error.message));
    await page.goto('http://localhost:5173');
    await page.getByRole('heading', { name: 'Обзор', exact: true }).waitFor();
    await page.screenshot({ path: process.env.TEMP + '/sergeek-desktop.png', fullPage: true });
    assert.equal(await page.locator('html').getAttribute('lang'), 'ru');
    assert.equal(await page.locator('.demo-badge').count(), 0);
    await page.getByRole('button', { name: /Портфель кампаний/ }).click();
    assert.equal(await page.locator('tbody tr').count(), 5);
    await page.locator('select').first().selectOption('Call');
    assert.equal(await page.locator('tbody tr').count(), 1);
    await page.locator('tbody tr').first().click();
    await page.getByRole('dialog').waitFor();
    await page.getByRole('button', { name: 'Закрыть детали кампании' }).click();
    await page.getByRole('button', { name: /Работа агента/ }).click();
    assert.equal(await page.locator('.pilot-row').count(), 17);
    await page.getByRole('button', { name: /Симуляция/, exact: false }).first().click();
    const responsePromise = page.waitForResponse(
      r => r.url().endsWith('/api/simulations/run') && r.request().method() === 'POST',
      { timeout: 120000 },
    );
    await page.getByRole('button', { name: 'Запустить симуляцию', exact: true }).click();
    const response = await responsePromise;
    assert.equal(response.status(), 200);
    const result = await response.json();
    assert.equal(result.runs, 10);
    assert.equal(result.seed_start, 20, 'A saved 10–19 range must continue at 20');
    assert.equal(result.values.length, 10);
    await page.getByRole('status').filter({ hasText: 'Симуляция завершена' }).waitFor();
    await page.reload();
    await page.getByRole('heading', { name: 'Обзор', exact: true }).waitFor();
    await page.getByRole('button', { name: /Симуляция/, exact: false }).first().click();
    const nextResponse = page.waitForResponse(
      r => r.url().endsWith('/api/simulations/run') && r.request().method() === 'POST',
      { timeout: 120000 },
    );
    await page.getByRole('button', { name: 'Запустить симуляцию', exact: true }).click();
    assert.equal((await (await nextResponse).json()).seed_start, 30,
      'Reload must preserve continuation at 30');
    await page.getByRole('status').filter({ hasText: 'Симуляция завершена' }).waitFor();
    await page.getByRole('button', { name: /Данные и лимиты/ }).click();
    assert.equal(await page.locator('.channel-table tbody tr').count(), 4);
    await page.setViewportSize({ width: 390, height: 844 });
    await page.getByRole('button', { name: /Обзор/ }).click();
    await page.screenshot({ path: process.env.TEMP + '/sergeek-mobile.png', fullPage: true });
    const dimensions = await page.evaluate(() => ({
      scroll: document.documentElement.scrollWidth, viewport: innerWidth,
    }));
    assert.ok(dimensions.scroll <= dimensions.viewport + 2, JSON.stringify(dimensions));
    assert.deepEqual(errors, []);
    await page.route('**/api/**', route => route.abort());
    await page.reload();
    await page.locator('.demo-badge').waitFor();
    await page.getByRole('button', { name: /Портфель кампаний/ }).click();
    assert.equal(await page.locator('tbody tr').count(), 5);
    console.log('PASS: Russian pages, API data, filters, dialog, 17 pilots, live simulation, mobile layout, offline fallback');
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
