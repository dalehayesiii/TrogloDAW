import { expect, test } from '@playwright/test';
import { execFileSync } from 'node:child_process';

const headers = { 'X-TrogloDAW-Request': '1' };
async function createPrior(request, name) {
  const library = await (await request.get('/api/library')).json();
  const fixture = JSON.parse(
    execFileSync(
      process.env.TROGLODAW_TEST_PYTHON || 'uv',
      process.env.TROGLODAW_TEST_PYTHON
        ? ['scripts/seed_browser_fixture.py']
        : ['run', '--locked', 'python', 'scripts/seed_browser_fixture.py'],
      { env: { ...process.env, TROGLODAW_LIBRARY: library.library }, encoding: 'utf8' },
    ),
  );
  const response = await request.post('/api/jobs', {
    headers,
    data: { action: 'organize', values: { id: fixture.song.id, name } },
  });
  const job = await response.json();
  await expect
    .poll(async () => (await (await request.get('/api/jobs/' + job.id)).json()).status)
    .toBe('complete');
}

function wave() {
  const rate = 8000,
    count = rate;
  const buffer = Buffer.alloc(44 + count * 2);
  buffer.write('RIFF');
  buffer.writeUInt32LE(36 + count * 2, 4);
  buffer.write('WAVEfmt ', 8);
  buffer.writeUInt32LE(16, 16);
  buffer.writeUInt16LE(1, 20);
  buffer.writeUInt16LE(1, 22);
  buffer.writeUInt32LE(rate, 24);
  buffer.writeUInt32LE(rate * 2, 28);
  buffer.writeUInt16LE(2, 32);
  buffer.writeUInt16LE(16, 34);
  buffer.write('data', 36);
  buffer.writeUInt32LE(count * 2, 40);
  for (let index = 0; index < count; index++)
    buffer.writeInt16LE(
      Math.round(3000 * Math.sin((index * 2 * Math.PI * 220) / rate)),
      44 + index * 2,
    );
  return buffer;
}

test('Library songs add without confirmation and preserve mixed recording drafts', async ({
  page,
  request,
}, testInfo) => {
  await createPrior(request, 'Source routing prior one');
  await createPrior(request, 'Source routing prior two');
  const setup = !(await (await request.get('/api/library')).json()).storage.setup_seen;
  await page.goto('/');
  if (setup) await page.getByRole('button', { name: 'Set up later', exact: true }).click();
  await expect(page.getByRole('dialog')).not.toBeVisible();
  await expect(page.getByLabel('Number of Generations', { exact: true })).toHaveValue('2');
  await page.getByLabel('Input Lyrics', { exact: true }).fill('Keep every word. No replacement.');
  await page.getByLabel('Input Styles', { exact: true }).fill('spoken, dry voice, no music');
  await page.getByLabel('Number of Generations', { exact: true }).fill('1');
  await expect
    .poll(async () =>
      page.evaluate(
        () => JSON.parse(localStorage.getItem('troglodaw-generation-draft') || '{}').lyrics,
      ),
    )
    .toBe('Keep every word. No replacement.');
  await page.getByLabel('Add audio files').setInputFiles([
    { name: 'recording one.wav', mimeType: 'audio/wav', buffer: wave() },
    { name: 'recording two.wav', mimeType: 'audio/wav', buffer: wave() },
  ]);
  await expect(page.locator('.clip-card')).toHaveCount(2);
  await expect(page.getByLabel('Input Lyrics', { exact: true })).toHaveValue(
    'Keep every word. No replacement.',
  );
  for (const [index, name] of ['Source routing prior one', 'Source routing prior two'].entries()) {
    await page.getByRole('tab', { name: 'Library', exact: true }).click();
    await page.locator('#panel-1 .song-row').filter({ hasText: name }).click();
    await page.getByRole('button', { name: 'Use as Input Audio', exact: true }).click();
    await expect(page.getByRole('dialog')).not.toBeVisible();
    await expect(page.locator('.clip-card')).toHaveCount(index + 3);
    await expect(page.getByLabel('Input Lyrics', { exact: true })).toHaveValue(
      'Keep every word. No replacement.',
    );
    await expect(page.getByLabel('Input Styles', { exact: true })).toHaveValue(
      'spoken, dry voice, no music',
    );
    await expect(page.getByLabel('Number of Generations', { exact: true })).toHaveValue('1');
  }
  await expect(page.getByRole('button', { name: 'Choose prior-song defaults' })).toHaveCount(0);
  await page.reload();
  await expect(page.locator('.clip-card')).toHaveCount(4);
  await expect(page.getByRole('dialog')).not.toBeVisible();
  await expect(page.locator('.clip-card').first()).toContainText('Audio recording');
  await expect(page.locator('.clip-card').last()).toContainText('Prior song');
  for (const theme of ['dark', 'light']) {
    if ((await page.locator('html').getAttribute('data-theme')) !== theme)
      await page
        .getByRole('button', { name: theme === 'dark' ? 'Dark mode' : 'Light mode', exact: true })
        .click();
    for (const width of [1440, 390]) {
      await page.setViewportSize({ width, height: 1000 });
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(
        true,
      );
      await page
        .locator('.input-stone')
        .screenshot({ path: testInfo.outputPath(`source-routing-${theme}-${width}.png`) });
    }
  }
});
