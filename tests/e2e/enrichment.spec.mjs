import { expect, test } from '@playwright/test';
import { spawn } from 'node:child_process';
import { mkdtempSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { createServer } from 'node:net';

test('one enrichment choice preserves editor words and uses checked preparation once', async ({
  page,
}) => {
  const folder = mkdtempSync(join(tmpdir(), 'troglodaw-enrichment-browser-'));
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
    JSON.stringify({ library_dir: join(folder, 'library'), model_dir: join(folder, 'models') }),
  );
  const python = process.env.TROGLODAW_TEST_PYTHON;
  const child = spawn(
    python || 'uv',
    python
      ? ['scripts/serve_planner_fixture.py', '--enrichment', '--port', String(port)]
      : [
          'run',
          '--locked',
          'python',
          'scripts/serve_planner_fixture.py',
          '--enrichment',
          '--port',
          String(port),
        ],
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
    const toggle = page.getByRole('checkbox', { name: 'Enrich prompt', exact: true });
    await expect(toggle).toBeChecked();
    await expect(toggle).toBeEnabled();
    await page.getByLabel('Input Styles', { exact: true }).fill('folk, warm guitar');
    const lyrics = '[Verse]\nFuck their promises. Every word stays.';
    await page.getByLabel('Input Lyrics', { exact: true }).fill(lyrics);
    await page.getByRole('button', { name: 'Generate songs', exact: true }).click();
    await expect(toggle).toBeDisabled();
    await expect(
      page.getByRole('heading', { name: 'Song generation output', exact: true }),
    ).toHaveCount(2);
    let calls = await (await page.request.get(base + '/api/fixture/calls')).json();
    expect(calls.filter((call) => call.action === 'enrich_prompt')).toHaveLength(1);
    expect(calls.filter((call) => call.action === 'generate')).toHaveLength(2);
    expect(calls[0].action).toBe('enrich_prompt');
    expect(calls[0].values).not.toHaveProperty('lyrics');
    const items = (await (await page.request.get(base + '/api/library')).json()).items;
    expect(items).toHaveLength(2);
    for (const item of items) {
      expect(item.recipe.draft.styles).toBe('folk, warm guitar');
      expect(item.recipe.parameters.lyrics).toBe(lyrics);
      expect(item.recipe.prompt_enrichment.applied).toBe(true);
      expect(item.recipe.parameters.caption).toContain('warm rhythmic guitar accents');
    }
    await expect(page.getByLabel('Input Styles', { exact: true })).toHaveValue('folk, warm guitar');
    await expect(page.getByLabel('Input Lyrics', { exact: true })).toHaveValue(lyrics);
    await expect(page.getByText('warm rhythmic guitar accents', { exact: true })).toHaveCount(0);
    await toggle.uncheck();
    await page.reload();
    await expect(toggle).not.toBeChecked();
    await page.getByLabel('Number of Generations', { exact: true }).fill('1');
    await page.getByRole('button', { name: 'Generate song', exact: true }).click();
    await expect(
      page.getByRole('heading', { name: 'Song generation output', exact: true }),
    ).toHaveCount(1);
    calls = await (await page.request.get(base + '/api/fixture/calls')).json();
    expect(calls.filter((call) => call.action === 'enrich_prompt')).toHaveLength(1);
    await toggle.check();
    await page.getByLabel('Input Styles', { exact: true }).fill('fail enrichment');
    const before = calls.length;
    await page.getByRole('button', { name: 'Generate song', exact: true }).click();
    await expect
      .poll(async () => (await (await page.request.get(base + '/api/fixture/calls')).json()).length)
      .toBeGreaterThanOrEqual(before + 3);
    await expect(page.getByRole('button', { name: 'Generate song', exact: true })).toBeEnabled();
    const later = (await (await page.request.get(base + '/api/library')).json()).items;
    const fallback = later.find((item) => item.recipe.draft.styles === 'fail enrichment');
    expect(fallback.recipe.prompt_enrichment.applied).toBe(false);
    expect(fallback.recipe.parameters.caption).toBe('fail enrichment');
    await page.request.post(base + '/api/fixture/missing-support', {
      headers: { 'X-TrogloDAW-Request': '1' },
    });
    await page.reload();
    await expect(page.getByText(/Supporting files are not installed yet/)).toBeVisible();
    await expect(toggle).toBeChecked();
    await expect(toggle).toBeEnabled();
    for (const theme of ['dark', 'light']) {
      for (const width of [1440, 390]) {
        await page.setViewportSize({ width, height: 1100 });
        await page.evaluate((value) => localStorage.setItem('troglodaw-theme', value), theme);
        await page.reload();
        await expect(page.locator('html')).toHaveAttribute('data-theme', theme);
        await expect(page.getByText(/Supporting files are not installed yet/)).toBeVisible();
        await expect(
          page.getByRole('button', { name: 'Generate song', exact: true }),
        ).toBeEnabled();
        await expect(toggle).toBeVisible();
        expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(
          true,
        );
        await page.screenshot({
          path: `test-results/enrichment-${theme}-${width}.png`,
          fullPage: true,
        });
      }
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
