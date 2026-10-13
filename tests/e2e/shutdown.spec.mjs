import { expect, test } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

const headers = { 'X-TrogloDAW-Request': '1' };
async function open(page) {
  const setup = !(await (await page.request.get('/api/library')).json()).storage.setup_seen;
  await page.goto('/');
  if (setup) await page.getByRole('button', { name: 'Set up later', exact: true }).click();
  await expect(page.getByRole('tab').first()).toBeVisible();
}
test('narrow layout and shutdown stay usable', async ({ page, request }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await open(page);
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);
  await page.getByRole('tab', { name: 'Vocal FX', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Choose a Library song' })).toBeVisible();
  await page.route('**/api/shutdown', (route) =>
    route.fulfill({
      status: 503,
      contentType: 'application/json',
      body: JSON.stringify({
        detail: 'Synthetic shutdown failure; retry Quit.',
      }),
    }),
  );
  await page.getByRole('button', { name: 'Quit', exact: true }).click();
  await expect(page.getByRole('alert')).toContainText('Synthetic shutdown failure');
  await expect(page.getByRole('tab')).toHaveCount(3);
  await expect(page.getByRole('button', { name: 'Quit', exact: true })).toBeEnabled();
  await page.unroute('**/api/shutdown');
  expect(
    (
      await request.post('/api/jobs', {
        data: { action: 'unknown', values: {} },
      })
    ).status(),
  ).toBe(403);
  expect(
    (
      await request.post('/api/jobs', {
        headers,
        data: { action: 'unknown', values: {} },
      })
    ).status(),
  ).toBe(422);
  await page.getByRole('button', { name: 'Quit', exact: true }).click();
  await expect(page.getByRole('status').filter({ hasText: 'has stopped' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'TrogloDAW has stopped.' })).toBeFocused();
  await expect(page.getByText('You can close this window now.')).toBeVisible();
  await expect(page.getByRole('tab')).toHaveCount(0);
  await expect(page.getByRole('button')).toHaveCount(0);
  await expect(page.locator('audio, dialog, input')).toHaveCount(0);
  await expect
    .poll(async () => {
      try {
        return (await request.get('/api/health')).status();
      } catch {
        return 0;
      }
    })
    .toBe(0);
  for (const theme of ['dark', 'light']) {
    await page.emulateMedia({ colorScheme: theme });
    await expect(page.locator('html')).toHaveAttribute('data-theme', theme);
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(
      390,
    );
    const report = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa']).analyze();
    expect(report.violations).toEqual([]);
  }
});
