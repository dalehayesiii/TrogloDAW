import { expect, test } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { spawn } from 'node:child_process';
import { mkdtempSync, readFileSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { createServer } from 'node:net';

test('helper reload page reports missing status and recovers after restart', async ({ page }) => {
  const script = readFileSync('scripts/windows/app_update.ps1', 'utf8');
  const html = script.match(/\$body = @'\r?\n([\s\S]*?)\r?\n'@/)[1].replace('__VERSION__', '2.0.0');
  let missing = false;
  let restarted = false;
  let failed = false;
  await page.route('**/update-helper', (route) =>
    route.fulfill({
      contentType: 'text/html',
      body: restarted ? '<h1>Restarted app</h1>' : html,
    }),
  );
  await page.route('**/api/updates', (route) =>
    missing
      ? route.abort()
      : route.fulfill({
          json: {
            helper: !restarted,
            version: '2.0.0',
            phase: failed ? 'failed' : 'installing',
            message: failed
              ? 'Synthetic restart failed. Verified installer retained.'
              : 'Installing verified update',
          },
        }),
  );
  await page.clock.install();
  await page.goto('/update-helper');
  await expect(page.getByText('Installing verified update')).toBeVisible();
  missing = true;
  await page.clock.setSystemTime(Date.now() + 46000);
  await expect(page.getByRole('heading', { name: 'Update needs attention' })).toBeVisible();
  await expect(page.getByText(/Update status is unavailable/)).toBeVisible();
  missing = false;
  failed = true;
  await page.reload();
  await expect(page.getByText(/Synthetic restart failed/)).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Update needs attention' })).toBeVisible();
  restarted = true;
  await expect(page.getByRole('heading', { name: 'Restarted app' })).toBeVisible();
});

test('first-run background setup and verified update recovery use the real service', async ({
  page,
}) => {
  const root = mkdtempSync(join(tmpdir(), 'troglodaw-update-browser-'));
  const port = await new Promise((resolve) => {
    const listener = createServer();
    listener.listen(0, '127.0.0.1', () => {
      const port = listener.address().port;
      listener.close(() => resolve(port));
    });
  });
  const base = `http://127.0.0.1:${port}`;
  writeFileSync(
    join(root, 'config.local.json'),
    JSON.stringify({ library_dir: join(root, 'library'), model_dir: join(root, 'models') }),
  );
  const python = process.env.TROGLODAW_TEST_PYTHON;
  const child = spawn(
    python || 'uv',
    python
      ? ['scripts/serve_update_fixture.py', '--port', String(port)]
      : ['run', '--locked', 'python', 'scripts/serve_update_fixture.py', '--port', String(port)],
    {
      env: { ...process.env, TROGLODAW_CONFIG_DIR: root, TROGLODAW_LIBRARY: '' },
      windowsHide: true,
      stdio: 'ignore',
    },
  );
  const headers = { 'X-TrogloDAW-Request': '1' };
  const post = async (path, data = {}) => {
    const response = await page.request.post(base + path, { headers, data });
    expect(response.status()).toBe(200);
    return response;
  };
  try {
    if (process.env.TROGLODAW_SCREENSHOT_DIR)
      await page.addInitScript(() => localStorage.setItem('troglodaw-theme', 'dark'));
    await expect
      .poll(async () => {
        try {
          return (await page.request.get(base + '/api/health')).status();
        } catch {
          return 0;
        }
      })
      .toBe(200);
    await page.goto(base);
    const dialog = page.getByRole('dialog');
    await expect(dialog).toContainText('Welcome to TrogloDAW');
    const centered = await dialog.evaluate((el) => {
      const r = el.getBoundingClientRect();
      return (
        Math.abs((r.left + r.right) / 2 - innerWidth / 2) < 2 &&
        Math.abs((r.top + r.bottom) / 2 - innerHeight / 2) < 2
      );
    });
    expect(centered).toBe(true);
    await expect(dialog.getByText('App updates', { exact: true })).toHaveCount(0);
    if (process.env.TROGLODAW_SCREENSHOT_DIR)
      await page.screenshot({ path: join(process.env.TROGLODAW_SCREENSHOT_DIR, 'setup-dark.png') });
    await post('/api/fixture/setup');
    await page
      .getByRole('button', { name: 'Install / verify selected model', exact: true })
      .click();
    await expect(
      page.getByRole('button', { name: 'Continue in background', exact: true }),
    ).toBeVisible();
    await page.getByRole('button', { name: 'Continue in background', exact: true }).click();
    await expect(dialog).not.toBeVisible();
    await expect(page.locator('footer .app-version')).toHaveText('TrogloDAW v1.0.0');
    await expect(page.getByLabel('Model installation in background')).toContainText('record');
    await expect(page.getByRole('button', { name: /^Generate songs?$/ })).toBeDisabled();
    const samples = Buffer.alloc(44 + 4410 * 2);
    samples.write('RIFF');
    samples.writeUInt32LE(samples.length - 8, 4);
    samples.write('WAVEfmt ', 8);
    samples.writeUInt32LE(16, 16);
    samples.writeUInt16LE(1, 20);
    samples.writeUInt16LE(1, 22);
    samples.writeUInt32LE(44100, 24);
    samples.writeUInt32LE(88200, 28);
    samples.writeUInt16LE(2, 32);
    samples.writeUInt16LE(16, 34);
    samples.write('data', 36);
    samples.writeUInt32LE(samples.length - 44, 40);
    for (let index = 0; index < 4410; index++)
      samples.writeInt16LE(
        Math.round(6000 * Math.sin((2 * Math.PI * 220 * index) / 44100)),
        44 + index * 2,
      );
    await page
      .getByLabel('Add audio files')
      .setInputFiles({ name: 'background-import.wav', mimeType: 'audio/wav', buffer: samples });
    await expect(page.locator('.clip-card')).toHaveCount(1, { timeout: 5000 });
    await expect(page.getByLabel('Model installation in background')).toBeVisible();
    await page.getByLabel('Input Lyrics', { exact: true }).fill('Keep my draft through upgrade');
    await page.reload();
    await expect(dialog).not.toBeVisible();
    await expect(page.getByLabel('Processing jobs')).toContainText('Download + installation');
    await expect(page.getByLabel('Processing jobs')).toContainText('Overall download');
    await expect(page.getByRole('button', { name: 'Dismiss Model setup notice' })).toHaveCount(0);
    await expect(page.getByLabel('Processing jobs')).not.toContainText('Whole request');
    if (process.env.TROGLODAW_SCREENSHOT_DIR)
      await page.setViewportSize({ width: 1440, height: 1600 });
    if (process.env.TROGLODAW_SCREENSHOT_DIR) await page.evaluate(() => window.scrollTo(0, 0));
    if (process.env.TROGLODAW_SCREENSHOT_DIR)
      await page.screenshot({
        path: join(process.env.TROGLODAW_SCREENSHOT_DIR, 'setup-background-dark.png'),
      });
    await page
      .getByLabel('Processing jobs')
      .getByRole('button', { name: 'Cancel', exact: true })
      .click();
    await expect(page.getByLabel('Model installation in background')).toHaveCount(0);
    await expect(page.getByRole('button', { name: 'Dismiss Model setup notice' })).toBeVisible();
    await page.getByRole('button', { name: 'Dismiss Model setup notice' }).click();
    await page.reload();
    await expect(page.getByRole('button', { name: 'Dismiss Model setup notice' })).toHaveCount(0);
    const canceledJobs = (await (await page.request.get(base + '/api/jobs')).json()).jobs;
    expect(
      canceledJobs.some((job) => job.action === 'model_install' && job.status === 'canceled'),
    ).toBe(true);
    await page.getByRole('button', { name: 'Settings', exact: true }).click();
    await expect(dialog).toContainText('Settings and storage');
    expect(
      await dialog.evaluate((el) => {
        const r = el.getBoundingClientRect();
        return (
          Math.abs((r.left + r.right) / 2 - innerWidth / 2) < 2 &&
          Math.abs((r.top + r.bottom) / 2 - innerHeight / 2) < 2
        );
      }),
    ).toBe(true);
    await dialog.getByText('App updates', { exact: true }).click();
    const browserRelease = dialog.getByRole('link', { name: 'Open latest release in browser' });
    await expect(browserRelease).toHaveAttribute(
      'href',
      'https://github.com/dalehayesiii/music-maker/releases/latest',
    );
    await expect(browserRelease).toHaveAttribute('target', '_blank');
    await expect(dialog).toContainText('Release access:');
    await expect(dialog).toContainText('2.0.0');
    await post('/api/fixture/check-delay', { seconds: 2 });
    await dialog.getByRole('button', { name: 'Check for updates', exact: true }).click();
    await expect(dialog).toContainText('Checking for the latest release');
    await expect(dialog.getByRole('button', { name: /Checking for updates/ })).toBeDisabled();
    await expect(dialog.getByRole('button', { name: 'Download 2.0.0', exact: true })).toBeVisible();
    await page.route(base + '/api/updates', (route) => route.abort());
    await dialog.getByRole('button', { name: 'Check for updates', exact: true }).click();
    await expect(dialog).toContainText('Could not read update status');
    await page.unroute(base + '/api/updates');
    await expect(dialog.getByRole('button', { name: 'Download 2.0.0', exact: true })).toBeVisible();
    await expect(dialog).not.toContainText('Could not read update status');
    await post('/api/fixture/check-delay', { seconds: 0 });
    if (process.env.TROGLODAW_SCREENSHOT_DIR)
      await page.screenshot({
        path: join(process.env.TROGLODAW_SCREENSHOT_DIR, 'updates-dark.png'),
      });
    for (const mode of ['dark', 'light']) {
      await page.evaluate((mode) => (document.documentElement.dataset.theme = mode), mode);
      expect(
        (await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze())
          .violations,
      ).toEqual([]);
    }
    await dialog.getByLabel('Check for updates on startup').uncheck();
    await expect
      .poll(
        async () => (await (await page.request.get(base + '/api/updates')).json()).check_on_startup,
      )
      .toBe(false);
    await dialog.getByRole('button', { name: 'Download 2.0.0', exact: true }).click();
    await expect(dialog).toContainText(/retry/i);
    await dialog.getByRole('button', { name: 'Download 2.0.0', exact: true }).click();
    await expect(
      dialog.getByRole('button', { name: 'Cancel update download', exact: true }),
    ).toBeVisible();
    await dialog.getByRole('button', { name: 'Cancel update download', exact: true }).click();
    await expect(dialog.getByRole('button', { name: 'Download 2.0.0', exact: true })).toBeVisible();
    await dialog.getByRole('button', { name: 'Download 2.0.0', exact: true }).click();
    const install = dialog.getByRole('button', { name: 'Install update and restart', exact: true });
    await expect(install).toBeEnabled();
    const client_id = 'ab123456-1234-1234-1234-123456789012';
    await post('/api/updates/capture', { client_id, active: true });
    await expect(install).toBeDisabled();
    await post('/api/updates/capture', { client_id, active: false });
    await post('/api/fixture/busy', { active: true });
    await expect(install).toBeDisabled();
    await post('/api/fixture/busy', { active: false });
    await expect(install).toBeEnabled();
    await install.click();
    await expect(dialog.getByRole('alert')).toContainText('launch');
    await expect(page.getByRole('tab')).toHaveCount(3);
    await page.clock.install();
    await page.route(base + '/api/updates', (route) => route.abort());
    await install.click();
    await expect(
      page.getByRole('heading', { name: 'Updating TrogloDAW', exact: true }),
    ).toBeVisible();
    await expect(page.getByRole('tab')).toHaveCount(0);
    await page.clock.setSystemTime(Date.now() + 46000);
    await expect(
      page.getByRole('heading', { name: 'Update needs attention', exact: true }),
    ).toBeVisible();
    await expect(page.getByText(/Update status is unavailable/)).toBeVisible();
    await expect(page.getByRole('link', { name: 'View the latest release' })).toBeVisible();
    for (const theme of ['light', 'dark']) {
      await page.emulateMedia({ colorScheme: theme });
      for (const width of [1440, 390]) {
        await page.setViewportSize({ width, height: 900 });
        expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(
          width,
        );
        await page.screenshot({
          path: test.info().outputPath(`update-status-${theme}-${width}.png`),
        });
      }
    }
    await page.unroute(base + '/api/updates');
    await expect(page.getByRole('tab')).toHaveCount(3);
    await expect(dialog).not.toBeVisible();
    await expect(page.getByLabel('Input Lyrics', { exact: true })).toHaveValue(
      'Keep my draft through upgrade',
    );
    await expect(page.locator('footer .app-version')).toHaveText('TrogloDAW v2.0.0');
    await page.getByRole('button', { name: 'Settings', exact: true }).click();
    await dialog.getByText('App updates', { exact: true }).click();
    await expect(dialog).toContainText('Installed version: 2.0.0');
    await expect(dialog.getByLabel('Check for updates on startup')).not.toBeChecked();
  } finally {
    await post('/api/fixture/stop').catch(() => {});
    await Promise.race([
      new Promise((resolve) => child.once('exit', resolve)),
      new Promise((resolve) => setTimeout(resolve, 3000)),
    ]);
    if (child.exitCode === null) child.kill();
  }
});
