import { expect, test } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { spawn } from 'node:child_process';
import { mkdtempSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { createServer } from 'node:net';

test('editable local lyrics and automatic sequential songs use the real service', async ({
  page,
}) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  const folder = mkdtempSync(join(tmpdir(), 'troglodaw-planning-browser-'));
  const port = await new Promise((resolve) => {
    const listener = createServer();
    listener.listen(0, '127.0.0.1', () => {
      const port = listener.address().port;
      listener.close(() => resolve(port));
    });
  });
  const base = `http://127.0.0.1:${port}`;
  writeFileSync(
    join(folder, 'config.local.json'),
    JSON.stringify({
      library_dir: join(folder, 'library'),
      model_dir: join(folder, 'models'),
      setup_seen: true,
    }),
  );
  const python = process.env.TROGLODAW_TEST_PYTHON;
  const child = spawn(
    python || 'uv',
    python
      ? ['scripts/serve_planner_fixture.py', '--port', String(port)]
      : ['run', '--locked', 'python', 'scripts/serve_planner_fixture.py', '--port', String(port)],
    {
      env: { ...process.env, TROGLODAW_CONFIG_DIR: folder, TROGLODAW_LIBRARY: '' },
      windowsHide: true,
      stdio: 'ignore',
    },
  );
  try {
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
    await expect(page.getByRole('button', { name: 'Settings', exact: true })).toBeEnabled();
    await expect(page.getByLabel('Number of Generations')).toHaveValue('2');
    await page.getByText('Write lyrics for me', { exact: true }).click();
    await page.getByLabel('Song idea', { exact: true }).fill('A song about purple cave lights');
    await page.getByLabel('Input Lyrics', { exact: true }).fill('Preserve until writing succeeds');
    await page.getByRole('button', { name: 'Generate lyrics', exact: true }).click();
    await expect(page.getByLabel('Input Lyrics', { exact: true })).toBeDisabled();
    await expect(page.getByLabel('Input Lyrics', { exact: true })).toHaveValue(
      '[Verse]\nPurple cave lights shine\nThese words are mine',
    );
    await expect(
      page.getByRole('complementary', { name: 'Notification', exact: true }),
    ).toContainText('Lyrics ready to edit');
    await page.getByRole('button', { name: 'Dismiss notification', exact: true }).click();
    await page.getByLabel('Input Lyrics', { exact: true }).fill('[Verse]\nMy edited cave song');
    await page.getByLabel('Song idea', { exact: true }).fill('fail');
    await page.getByRole('button', { name: 'Generate lyrics', exact: true }).click();
    await expect(page.getByText('Synthetic lyric failure', { exact: true }).first()).toBeVisible();
    await expect(page.getByLabel('Input Lyrics', { exact: true })).toHaveValue(
      '[Verse]\nMy edited cave song',
    );
    await page.getByLabel('Input Styles', { exact: true }).fill('folk, warm guitar');
    await page.getByRole('button', { name: 'Generate songs', exact: true }).click();
    await expect(
      page.getByRole('heading', { name: 'Song generation output', exact: true }),
    ).toHaveCount(2);
    const library = await (await page.request.get(base + '/api/library')).json();
    expect(library.items).toHaveLength(2);
    expect(
      library.items.every(
        (item) =>
          item.duration === 18 &&
          item.recipe.parameters.lyrics === '[Verse]\nMy edited cave song' &&
          item.recipe.parameters.duration_derivation.method === 'local-model-planner',
      ),
    ).toBe(true);
    expect(new Set(library.items.map((item) => item.recipe.parameters.seed)).size).toBe(2);
    await expect(page.getByLabel('Notification', { exact: true })).toHaveCount(0, {
      timeout: 12000,
    });
    await page.getByLabel('Number of Generations').fill('1');
    await page.reload();
    await expect(page.getByRole('button', { name: 'Settings', exact: true })).toBeEnabled();
    await expect(page.getByLabel('Input Lyrics', { exact: true })).toHaveValue(
      '[Verse]\nMy edited cave song',
    );
    await expect(page.getByLabel('Number of Generations')).toHaveValue('1');
    await expect(page.getByLabel('Notification', { exact: true })).toHaveCount(0);
    for (const theme of ['dark', 'light']) {
      await page.evaluate((value) => {
        localStorage.setItem('troglodaw-theme', value);
      }, theme);
      await page.reload();
      await expect(page.locator('html')).toHaveAttribute('data-theme', theme);
      await expect(page.getByRole('button', { name: 'Generate song', exact: true })).toBeEnabled();
      expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
    }
  } finally {
    await page.request
      .post(base + '/api/fixture/stop', { headers: { 'X-TrogloDAW-Request': '1' } })
      .catch(() => {});
    await Promise.race([
      new Promise((resolve) => child.once('exit', resolve)),
      new Promise((resolve) => setTimeout(resolve, 3000)),
    ]);
    if (child.exitCode === null) child.kill();
  }
});
