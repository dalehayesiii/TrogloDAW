import { expect, test } from '@playwright/test';

function recording(name = 'synthetic-recording.wav', hz = 220) {
  const rate = 8000,
    count = rate * 2,
    buffer = Buffer.alloc(44 + count * 2);
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
  for (let i = 0; i < count; i++)
    buffer.writeInt16LE(Math.round(1800 * Math.sin((2 * Math.PI * hz * i) / rate)), 44 + i * 2);
  return { name, mimeType: 'audio/wav', buffer };
}
async function open(page) {
  const setup = !(await (await page.request.get('/api/library')).json()).storage.setup_seen;
  await page.goto('/');
  if (setup) await page.getByRole('button', { name: 'Set up later', exact: true }).click();
  await expect(page.getByRole('dialog')).not.toBeVisible();
}

test('three flows preserve separate audio and text drafts through switching and reload', async ({
  page,
}, testInfo) => {
  await open(page);
  const panel = page.locator('#panel-0');
  await page.getByLabel('Input Lyrics', { exact: true }).fill('Keep these literal words');
  await page.getByLabel('Input Styles', { exact: true }).fill('dry spoken voice, no music');
  await page.locator('#audio-files').setInputFiles(recording('sampled.wav'));
  await expect(panel.locator('.clip-card')).toHaveCount(1);
  await panel.getByText('Audio arrangement settings', { exact: true }).click();
  await expect(page.getByLabel('Mix samples after generation', { exact: true })).not.toBeChecked();
  await page.getByLabel('Mix samples after generation', { exact: true }).check();
  await page.getByLabel('Generation workflow', { exact: true }).selectOption('recording-style');
  await expect(panel.locator('.clip-card')).toHaveCount(0);
  await expect(page.getByLabel('Input Lyrics', { exact: true })).not.toBeVisible();
  await expect(panel.getByText('Write lyrics for me', { exact: true })).not.toBeVisible();
  await expect(
    panel.getByRole('button', { name: 'Choose from Library', exact: true }),
  ).not.toBeVisible();
  await expect(
    panel.getByRole('button', { name: 'Prior Song Reference', exact: true }),
  ).not.toBeVisible();
  expect(await page.locator('#audio-files').evaluate((input) => input.multiple)).toBe(false);
  await page.getByLabel('Input Styles', { exact: true }).fill('warm acoustic folk');
  await page.locator('#audio-files').setInputFiles(recording('intact.wav', 330));
  await expect(panel.locator('.clip-card')).toHaveCount(1);
  await expect(panel.locator('.clip-card input').first()).toHaveValue(/intact/i);
  await panel.getByText('More Options', { exact: true }).click();
  await expect(panel.getByLabel(/Duration \(auto/)).not.toBeVisible();
  await expect(panel.getByText('Clip adjustments', { exact: true })).not.toBeVisible();
  for (const theme of ['dark', 'light']) {
    await page.evaluate((theme) => {
      document.documentElement.classList.toggle('dark', theme === 'dark');
      document.documentElement.setAttribute('data-theme', theme);
    }, theme);
    for (const width of [1440, 390]) {
      await page.setViewportSize({ width, height: 1000 });
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(
        true,
      );
      await panel.screenshot({ path: testInfo.outputPath(`recording-${theme}-${width}.png`) });
    }
  }
  await page.reload();
  await expect(page.getByLabel('Generation workflow', { exact: true })).toHaveValue(
    'recording-style',
  );
  await expect(page.getByLabel('Input Styles', { exact: true })).toHaveValue('warm acoustic folk');
  await expect(panel.locator('.clip-card input').first()).toHaveValue(/intact/i);
  await page.getByLabel('Generation workflow', { exact: true }).selectOption('arrange-over-song');
  await expect(page.getByLabel('Backing song', { exact: true })).toBeVisible();
  await expect(page.getByLabel('Input Styles', { exact: true })).not.toBeVisible();
  await page.getByLabel('Generation workflow', { exact: true }).selectOption('model');
  await expect(page.getByLabel('Input Lyrics', { exact: true })).toHaveValue(
    'Keep these literal words',
  );
  await expect(page.getByLabel('Input Styles', { exact: true })).toHaveValue(
    'dry spoken voice, no music',
  );
  await expect(panel.locator('.clip-card input').first()).toHaveValue(/sampled/i);
  await panel.getByText('Audio arrangement settings', { exact: true }).click();
  await expect(page.getByLabel('Mix samples after generation', { exact: true })).toBeChecked();
});

test('mode tooltips explain conditioning, independent postmix and adherence with keyboard and tap', async ({
  page,
}, testInfo) => {
  await open(page);
  await page.locator('#audio-files').setInputFiles(recording());
  await expect(page.locator('#panel-0 .clip-card')).toHaveCount(1);
  await page.getByText('Audio arrangement settings', { exact: true }).click();
  const help = page.getByRole('button', { name: 'Sample mixing guidance', exact: true });
  await help.focus();
  await expect(page.locator('#postmix-guidance')).toContainText(
    'model hears your complete transformed arrangement',
  );
  await expect(page.locator('#postmix-guidance')).toContainText('model generates independently');
  await help.press('Escape');
  await expect(page.locator('#postmix-guidance')).not.toBeVisible();
  await help.click();
  await expect(page.locator('#postmix-guidance')).toBeVisible();
  const adherence = page.getByRole('button', { name: 'Audio adherence guidance', exact: true });
  await adherence.hover();
  await expect(page.locator('#adherence-guidance')).toContainText('no effect in postmix mode');
  for (const theme of ['light', 'dark']) {
    if ((await page.locator('html').getAttribute('data-theme')) !== theme)
      await page
        .getByRole('button', { name: theme === 'dark' ? 'Dark mode' : 'Light mode', exact: true })
        .click();
    for (const width of [1440, 390]) {
      await page.setViewportSize({ width, height: 1000 });
      await page.getByLabel('Input Styles', { exact: true }).focus();
      await help.focus();
      const box = await page.locator('#postmix-guidance').boundingBox();
      expect(box.x).toBeGreaterThanOrEqual(0);
      expect(box.x + box.width).toBeLessThanOrEqual(width);
      await page
        .locator('.audio-arrangement-settings')
        .screenshot({ path: testInfo.outputPath(`sampled-guidance-${theme}-${width}.png`) });
      await help.press('Escape');
      await adherence.focus();
      const audioBox = await page.locator('#adherence-guidance').boundingBox();
      expect(audioBox.x).toBeGreaterThanOrEqual(0);
      expect(audioBox.x + audioBox.width).toBeLessThanOrEqual(width);
      await adherence.press('Escape');
    }
  }
  await page.getByLabel('Mix samples after generation', { exact: true }).check();
  await expect(page.locator('#audio-adherence')).not.toBeVisible();
  await page.reload();
  await page.getByText('Audio arrangement settings', { exact: true }).click();
  await expect(page.getByLabel('Mix samples after generation', { exact: true })).toBeChecked();
});

test('direct recording replacement keeps one source and clears neither other workflow nor prior take on failure', async ({
  page,
}) => {
  await open(page);
  await page.getByLabel('Generation workflow', { exact: true }).selectOption('recording-style');
  await page.locator('#audio-files').setInputFiles(recording('first.wav'));
  await expect(page.locator('#panel-0 .clip-card input').first()).toHaveValue(/first/i);
  await page.locator('#audio-files').setInputFiles({
    name: 'invalid.wav',
    mimeType: 'audio/wav',
    buffer: Buffer.from('not audio'),
  });
  await expect(page.locator('#panel-0 .clip-card input').first()).toHaveValue(/first/i);
  await expect(
    page.getByRole('region', { name: 'Input Audio notifications', exact: true }),
  ).toBeVisible();
  await page.setViewportSize({ width: 390, height: 844 });
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth),
  ).toBeTruthy();
  await page.locator('#audio-files').setInputFiles(recording('second.wav', 440));
  await expect(page.locator('#panel-0 .clip-card input').first()).toHaveValue(/second/i);
  await expect(page.locator('#panel-0 .clip-card')).toHaveCount(1);
});
