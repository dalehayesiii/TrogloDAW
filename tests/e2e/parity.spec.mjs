import { expect, test } from '@playwright/test';

test('all original tabs, controls and defaults remain available', async ({ page }) => {
  const errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.goto('/');
  await expect(page.getByRole('tab')).toHaveText([
    '🎤 AI Producer',
    'Voice FX',
    'Generator',
    'Mixer / Remix',
  ]);
  await page.getByRole('button', { name: /Optional overrides/ }).click();
  await expect(page.getByLabel('Style', { exact: true })).toHaveValue('auto');
  await expect(page.getByLabel('BPM (0 = detect)', { exact: true })).toHaveValue('0');
  await expect(
    page.getByLabel('Seed (-1 = random; reuse a seed to reproduce)', { exact: true }),
  ).toHaveValue('-1');
  await page.getByRole('tab', { name: 'Voice FX', exact: true }).click();
  await expect(page.getByLabel('Normalize', { exact: true })).toBeChecked();
  await expect(page.getByLabel('Trim silence', { exact: true })).not.toBeChecked();
  await expect(page.getByLabel('Pitch (semitones)', { exact: true })).toHaveValue('0');
  await expect(page.getByLabel('Echo time s', { exact: true })).toHaveValue('0.3');
  await page.getByRole('tab', { name: 'Generator', exact: true }).click();
  await expect(page.getByLabel('BPM', { exact: true })).toHaveValue('90');
  await expect(page.getByLabel('Drum style', { exact: true })).toHaveValue('boombap');
  await expect(page.getByLabel('Length (bars)', { exact: true })).toHaveValue('8');
  await page.getByRole('tab', { name: 'Mixer / Remix', exact: true }).click();
  await expect(page.getByLabel('Music volume dB', { exact: true })).toHaveValue('-4');
  await expect(page.getByLabel('Voice offset (s)', { exact: true })).toHaveValue('2');
  await expect(page.getByLabel('Duck music under vocals', { exact: true })).toBeChecked();
  await page.getByRole('button', { name: 'Render mix', exact: true }).click();
  await expect(page.locator('#mix-status')).toHaveValue('Pick a voice and a music track.');
  expect(errors).toEqual([]);
});

test('upload, library, effects, generate, mix, recipe, produce and download use real Python', async ({
  page,
  request,
}) => {
  await page.goto('/');
  // Tiny synthetic PCM WAV avoids fixtures containing personal audio.
  const samples = 44100 * 2,
    buffer = Buffer.alloc(44 + samples * 2);
  buffer.write('RIFF', 0);
  buffer.writeUInt32LE(buffer.length - 8, 4);
  buffer.write('WAVEfmt ', 8);
  buffer.writeUInt32LE(16, 16);
  buffer.writeUInt16LE(1, 20);
  buffer.writeUInt16LE(1, 22);
  buffer.writeUInt32LE(44100, 24);
  buffer.writeUInt32LE(88200, 28);
  buffer.writeUInt16LE(2, 32);
  buffer.writeUInt16LE(16, 34);
  buffer.write('data', 36);
  buffer.writeUInt32LE(samples * 2, 40);
  for (let i = 0; i < samples; i++)
    buffer.writeInt16LE(Math.round(Math.sin((i * 2 * Math.PI * 165) / 44100) * 9000), 44 + i * 2);
  await page
    .locator('input#library-upload')
    .setInputFiles({ name: 'synthetic-test.wav', mimeType: 'audio/wav', buffer });
  await page.getByRole('button', { name: 'Import uploads', exact: true }).click();
  await expect(page.locator('#library-status')).toHaveValue(/Imported synthetic-test/);
  let items = (await (await request.get('/api/library')).json()).items;
  const voice = items.find((i) => i.name === 'synthetic-test');
  await page.getByLabel('Select item', { exact: true }).selectOption(voice.id);
  await expect(page.locator('.code-panel pre')).toContainText(voice.id);
  await page.getByLabel('Rename', { exact: true }).fill('parity voice');
  await page.getByLabel('Set tags', { exact: true }).fill('test,parity');
  await page.getByRole('button', { name: 'Save name/tags', exact: true }).click();
  await expect(page.locator('#library-status')).toHaveValue('Updated.');
  await page.getByRole('tab', { name: 'Voice FX', exact: true }).click();
  await page.locator('#fxVoice').selectOption(voice.id);
  await page.getByRole('button', { name: 'Preview', exact: true }).click();
  await expect(page.locator('#fx-status')).toHaveValue('Preview only (not saved)');
  await page.getByRole('button', { name: 'Apply & save as new voice', exact: true }).click();
  await expect(page.locator('#fx-status')).toHaveValue(/Saved new voice/);
  await page.getByRole('tab', { name: 'Generator', exact: true }).click();
  await page.getByLabel('Length (bars) value', { exact: true }).fill('1');
  await page.getByLabel('Seed (-1 = random)', { exact: true }).fill('42');
  await page.getByLabel('Name (optional)', { exact: true }).fill('parity beat');
  await page.getByRole('button', { name: 'Generate', exact: true }).click();
  await expect(page.locator('#generator-status')).toHaveValue(/Generated parity beat.*seed=42/);
  items = (await (await request.get('/api/library')).json()).items;
  const beat = items.find((i) => i.name === 'parity beat');
  await page.getByRole('tab', { name: 'Mixer / Remix', exact: true }).click();
  await page.locator('#mVoice').selectOption(voice.id);
  await page.locator('#mMusic').selectOption(beat.id);
  await page.getByLabel('Mix name (optional)', { exact: true }).fill('parity mix');
  await page.getByRole('button', { name: 'Render mix', exact: true }).click();
  await expect(page.locator('#mix-status')).toHaveValue(/Mixed parity mix/);
  const download = page.waitForEvent('download');
  await page.locator('mm-download a:visible').click();
  expect((await download).suggestedFilename()).toMatch(/\.mp3$/);
  items = (await (await request.get('/api/library')).json()).items;
  const mix = items.find((i) => i.name === 'parity mix');
  await page.locator('#rmPick').selectOption(mix.id);
  await expect(page.locator('#mName')).toHaveValue('parity mix_remix');
  await expect(page.locator('#mVoice')).toHaveValue(voice.id);
  await page.getByRole('tab', { name: '🎤 AI Producer', exact: true }).click();
  await page.locator('#apVoice').selectOption(voice.id);
  await page.getByRole('button', { name: /Optional overrides/ }).click();
  await page.locator('#apBpm').fill('120');
  await page.locator('#apSeed').fill('42');
  await page.getByRole('button', { name: /PRODUCE MY SONG/ }).click();
  await expect(page.locator('.job-progress')).toBeVisible();
  await expect(page.locator('.production-info')).toContainText('42');
  await expect(page.locator('.production-info')).toContainText('LUFS');
  await page.locator('#libPick').selectOption(voice.id);
  await page.getByRole('button', { name: 'Delete item', exact: true }).click();
  await expect(page.locator('#library-status')).toHaveValue('Deleted parity voice');
  await expect(page.locator('#libPick')).toHaveValue('');
});

test('quit returns the original message and stops the local service', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('button', { name: '⏻ Quit Music Maker', exact: true }).click();
  await expect(page.locator('#library-status')).toHaveValue(
    'Music Maker has stopped. You can close this browser tab.',
  );
});
