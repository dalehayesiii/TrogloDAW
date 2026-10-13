import { expect, test } from '@playwright/test';

const headers = { 'X-TrogloDAW-Request': '1' };
function wave(seconds = 12, frequency = 110) {
  const rate = 8000,
    count = rate * seconds;
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
  for (let i = 0; i < count; i++) {
    const gap = seconds > 3 && i / rate > 5 && i / rate < 7;
    buffer.writeInt16LE(
      Math.round((gap ? 0 : 1500) * Math.sin((i * 2 * Math.PI * frequency) / rate)),
      44 + i * 2,
    );
  }
  return buffer;
}
async function open(page, request) {
  const setup = !(await (await request.get('/api/library')).json()).storage.setup_seen;
  await page.goto('/');
  if (setup) await page.getByRole('button', { name: 'Set up later', exact: true }).click();
  await expect(page.getByRole('dialog')).not.toBeVisible();
}
async function importWav(page, name, buffer = wave(), folder = '', testInfo) {
  await page.getByRole('tab', { name: 'Library', exact: true }).click();
  await page.getByRole('button', { name: 'Import WAV song', exact: true }).click();
  await page
    .getByLabel('WAV song file', { exact: true })
    .setInputFiles({ name: 'external.wav', mimeType: 'audio/wav', buffer });
  await page.getByLabel('Imported song title', { exact: true }).fill(name);
  await page.getByLabel('Imported song folder', { exact: true }).selectOption(folder);
  if (testInfo) {
    for (const theme of ['dark', 'light']) {
      await page.evaluate((theme) => {
        document.documentElement.classList.toggle('dark', theme === 'dark');
        document.documentElement.setAttribute('data-theme', theme);
      }, theme);
      for (const width of [1440, 390]) {
        await page.setViewportSize({ width, height: 1000 });
        const box = await page.getByRole('dialog').boundingBox();
        expect(Math.abs(box.x + box.width / 2 - width / 2)).toBeLessThan(2);
        expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(
          true,
        );
        await page
          .getByRole('dialog')
          .screenshot({ path: testInfo.outputPath(`import-${theme}-${width}.png`) });
      }
    }
    await page.setViewportSize({ width: 1440, height: 1000 });
  }
  await page.getByRole('button', { name: 'Import song', exact: true }).click();
}

test('WAV imports recover after errors and preserve folder, playback and prior classification', async ({
  page,
  request,
}, testInfo) => {
  await open(page, request);
  const created = await (
    await request.post('/api/jobs', {
      headers,
      data: { action: 'folder', values: { name: 'Imported fixture folder' } },
    })
  ).json();
  await expect
    .poll(async () => (await (await request.get('/api/jobs/' + created.id)).json()).status)
    .toBe('complete');
  await page.reload();
  await importWav(page, 'Corrupt import', Buffer.from('corrupt WAV'));
  await expect(
    page.getByRole('region', { name: 'Song import notifications', exact: true }),
  ).toContainText('not a readable WAV');
  await importWav(page, 'Imported retry song', wave(), 'Imported fixture folder', testInfo);
  await expect(
    page.getByRole('region', { name: 'Song import notifications', exact: true }),
  ).not.toBeVisible();
  await expect(
    page.locator('#panel-1 .song-row').filter({ hasText: 'Imported retry song' }),
  ).toBeVisible();
  const library = await (await request.get('/api/library')).json();
  const song = library.items.find((item) => item.name === 'Imported retry song');
  expect(song.folder).toBe('Imported fixture folder');
  const preview = await (await request.get('/api/items/' + song.id)).json();
  expect((await request.get(preview.audio.url)).ok()).toBe(true);
  await page.getByRole('button', { name: 'Use as Input Audio', exact: true }).click();
  await expect(page.locator('.clip-card')).toContainText('Prior song');
  await expect(page.getByRole('dialog')).not.toBeVisible();
  await page.reload();
  await expect(page.locator('.clip-card')).toContainText('Prior song');
});

test('preserved backing runs two sequential arrangements without models and keeps model drafts', async ({
  page,
  request,
}, testInfo) => {
  await open(page, request);
  await page.getByLabel('Input Lyrics', { exact: true }).fill('Keep this literal lyric');
  await page.getByLabel('Input Styles', { exact: true }).fill('dry spoken word, no music');
  await page.getByLabel('Generation workflow', { exact: true }).focus();
  await importWav(page, 'Fixed backing fixture');
  await expect(
    page.locator('#panel-1 .song-row').filter({ hasText: 'Fixed backing fixture' }),
  ).toBeVisible();
  await page.getByRole('tab', { name: 'Generation', exact: true }).click();
  await page.getByLabel('Generation workflow', { exact: true }).selectOption('arrange-over-song');
  await expect(page.getByLabel('Input Lyrics', { exact: true })).not.toBeVisible();
  await expect(page.getByLabel('Input Styles', { exact: true })).not.toBeVisible();
  await expect(
    page.getByRole('button', { name: 'Prior Song Reference', exact: true }),
  ).not.toBeVisible();
  const run = page.getByRole('button', { name: /^Arrange recordings/ });
  await expect(run).toBeDisabled();
  const library = await (await request.get('/api/library')).json();
  expect(library.models.ready).toBe(false);
  const backing = library.items.find((item) => item.name === 'Fixed backing fixture');
  await page.getByLabel('Backing song', { exact: true }).selectOption(backing.id);
  await expect(run).toBeDisabled();
  await page.getByLabel('Add audio files').setInputFiles([
    { name: 'quiet phrase.wav', mimeType: 'audio/wav', buffer: wave(2, 330) },
    { name: 'short accent.wav', mimeType: 'audio/wav', buffer: wave(1, 550) },
  ]);
  await expect(page.locator('.clip-card')).toHaveCount(2);
  await page.getByLabel('Song Title (optional)', { exact: true }).fill('Preserved backing result');
  await expect(run).toBeEnabled();
  const toast = page.getByRole('button', { name: 'Dismiss notification', exact: true });
  if (await toast.isVisible()) await toast.click();
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
        .locator('#panel-0')
        .screenshot({ path: testInfo.outputPath(`backing-${theme}-${width}.png`) });
    }
  }
  await run.click();
  await expect(
    page.locator('.song-output-title').filter({ hasText: 'Preserved backing result 1' }),
  ).toBeVisible();
  await expect(
    page.locator('.song-output-title').filter({ hasText: 'Preserved backing result 2' }),
  ).toBeVisible();
  const jobs = (await (await request.get('/api/jobs')).json()).jobs;
  const job = jobs.filter((item) => item.action === 'song_generate').at(-1);
  expect(job.status).toBe('complete');
  expect(job.result.outcomes.map((output) => output.status)).toEqual(['complete', 'complete']);
  for (const output of job.result.outcomes) {
    expect(output.parameters.duration).toBe(12);
    expect(output.song.recipe.model).toBeNull();
    expect(output.song.recipe.backing_song_id).toBe(backing.id);
    expect((await request.get(output.audio.url)).ok()).toBe(true);
  }
  await page.getByLabel('Generation workflow', { exact: true }).selectOption('model');
  await expect(page.getByLabel('Input Lyrics', { exact: true })).toHaveValue(
    'Keep this literal lyric',
  );
  await expect(page.getByLabel('Input Styles', { exact: true })).toHaveValue(
    'dry spoken word, no music',
  );
  await page.getByLabel('Generation workflow', { exact: true }).selectOption('arrange-over-song');
  await page.reload();
  await expect(page.getByLabel('Backing song', { exact: true })).toHaveValue(backing.id);
  await expect(page.locator('.clip-card')).toHaveCount(2);
});
