import { expect, test } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { execFileSync } from 'node:child_process';

const headers = { 'X-TrogloDAW-Request': '1' };
async function open(page) {
  await page.goto('/');
  const later = page.getByRole('button', { name: 'Set up later', exact: true });
  await expect(later).toBeVisible();
  await later.click();
}
function wave() {
  const rate = 44100,
    samples = rate;
  const buffer = Buffer.alloc(44 + samples * 2);
  buffer.write('RIFF', 0);
  buffer.writeUInt32LE(36 + samples * 2, 4);
  buffer.write('WAVEfmt ', 8);
  buffer.writeUInt32LE(16, 16);
  buffer.writeUInt16LE(1, 20);
  buffer.writeUInt16LE(1, 22);
  buffer.writeUInt32LE(rate, 24);
  buffer.writeUInt32LE(rate * 2, 28);
  buffer.writeUInt16LE(2, 32);
  buffer.writeUInt16LE(16, 34);
  buffer.write('data', 36);
  buffer.writeUInt32LE(samples * 2, 40);
  for (let i = 0; i < samples; i++)
    buffer.writeInt16LE(Math.round(6000 * Math.sin((2 * Math.PI * 220 * i) / rate)), 44 + i * 2);
  return buffer;
}
async function seed(request) {
  const library = await (await request.get('/api/library')).json();
  const command = process.env.TROGLODAW_TEST_PYTHON || 'uv';
  const args = process.env.TROGLODAW_TEST_PYTHON
    ? ['scripts/seed_browser_fixture.py']
    : ['run', '--locked', 'python', 'scripts/seed_browser_fixture.py'];
  return JSON.parse(
    execFileSync(command, args, {
      env: { ...process.env, TROGLODAW_LIBRARY: library.library },
      encoding: 'utf8',
    }),
  );
}

test('three workflows, progressive controls, drafts and accessible input help', async ({
  page,
}) => {
  const errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await open(page);
  await expect(page.getByRole('tab')).toHaveText(['Generation', 'Library', 'Vocal FX']);
  await expect(page.getByLabel('Number of Generations')).toHaveValue('1');
  await expect(page.getByLabel('Vocal Gender')).not.toBeVisible();
  await page.getByText('More Options', { exact: true }).click();
  await expect(page.getByLabel('Vocal Gender')).toHaveValue('');
  await expect(page.getByLabel('Duration (auto or 10–120 seconds)')).toHaveValue('auto');
  await page.getByLabel('Input Lyrics', { exact: true }).fill('Keep every word');
  await page.getByLabel('Input Styles', { exact: true }).fill('folk guitar');
  await page.getByRole('tab', { name: 'Library', exact: true }).click();
  await page.getByRole('tab', { name: 'Generation', exact: true }).click();
  await expect(page.getByLabel('Input Lyrics', { exact: true })).toHaveValue('Keep every word');
  const help = page.getByRole('button', { name: 'Audio input guidance' });
  await help.focus();
  await expect(page.getByRole('tooltip')).toContainText(
    'Audio inputs are intended to be vocal recordings',
  );
  await help.press('Escape');
  await expect(page.getByRole('tooltip')).not.toBeVisible();
  await help.hover();
  await expect(page.getByRole('tooltip')).toBeVisible();
  expect(errors).toEqual([]);
});

test('applicable audio conditioning controls persist and postmix disables adherence', async ({
  page,
}) => {
  await open(page);
  await expect(page.getByText('Audio arrangement settings', { exact: true })).toHaveCount(0);
  await page.getByLabel('Add audio files').setInputFiles({
    name: 'arrangement.wav',
    mimeType: 'audio/wav',
    buffer: wave(),
  });
  const settings = page.locator('.input-stone .audio-arrangement-settings');
  await expect(settings).not.toHaveAttribute('open');
  await settings.getByText('Audio arrangement settings', { exact: true }).click();
  await expect(page.getByLabel('Mix samples after generation')).not.toBeChecked();
  await page.getByLabel(/^Audio adherence/).fill('62');
  await page.getByRole('tab', { name: 'Library', exact: true }).click();
  await page.getByRole('tab', { name: 'Generation', exact: true }).click();
  await page.reload();
  await page.getByRole('button', { name: 'Set up later', exact: true }).click();
  await settings.getByText('Audio arrangement settings', { exact: true }).click();
  await expect(page.getByLabel(/^Audio adherence/)).toHaveValue('62');
  for (const mode of ['light', 'dark']) {
    if ((await page.locator('html').getAttribute('data-theme')) !== mode)
      await page
        .getByRole('button', { name: mode === 'light' ? 'Light mode' : 'Dark mode', exact: true })
        .click();
    await page.evaluate(async () => {
      await Promise.all(
        document
          .getAnimations()
          .filter((animation) => Number(animation.effect?.getTiming().iterations) !== Infinity)
          .map((animation) => animation.finished.catch(() => undefined)),
      );
    });
    expect(
      (await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze())
        .violations,
    ).toEqual([]);
  }
  await page.getByLabel('Mix samples after generation').check();
  await expect(page.getByLabel(/^Audio adherence/)).toHaveCount(0);
  await expect(settings).toContainText('Generate music independently');
  await page.reload();
  await page.getByRole('button', { name: 'Set up later', exact: true }).click();
  await settings.getByText('Audio arrangement settings', { exact: true }).click();
  await expect(page.getByLabel('Mix samples after generation')).toBeChecked();
  await page.getByRole('button', { name: 'Remove clip', exact: true }).click();
  await expect(settings).toHaveCount(0);
});

test('multiple real uploads, folders, prior-song choices and cached FX saves', async ({
  page,
  request,
}) => {
  const fixture = await seed(request);
  await open(page);
  await page.route('**/api/uploads', async (route) => {
    await new Promise((resolve) => setTimeout(resolve, 250));
    await route.continue();
  });
  await page.getByLabel('Add audio files').setInputFiles([
    { name: 'one.wav', mimeType: 'audio/wav', buffer: wave() },
    { name: 'two.wav', mimeType: 'audio/wav', buffer: wave() },
  ]);
  await expect(page.getByRole('button', { name: 'Generate song', exact: true })).toBeDisabled();
  await expect(page.locator('.clip-card')).toHaveCount(2);
  const uploadedAdjustments = page.locator('.input-stone .clip-card .clip-adjustments');
  await expect(uploadedAdjustments).toHaveCount(2);
  await expect(uploadedAdjustments.first()).not.toHaveAttribute('open');
  await expect(uploadedAdjustments.last()).not.toHaveAttribute('open');
  await page.getByText('Clip adjustments', { exact: true }).first().click();
  await expect(uploadedAdjustments.first().getByLabel('Pitch (semitones)')).toBeEnabled();
  await expect(uploadedAdjustments.first().getByLabel('Playback speed')).toBeEnabled();
  await expect(uploadedAdjustments.first().getByLabel('Volume (dB)')).toBeEnabled();
  await page.getByLabel('Replace this clip with a file').first().setInputFiles({
    name: 'replacement.wav',
    mimeType: 'audio/wav',
    buffer: wave(),
  });
  await expect(page.getByLabel('Clip label').first()).toHaveValue('replacement');
  await expect(page.getByLabel('Clip label').nth(1)).toHaveValue('two');
  await expect(page.locator('.clip-card')).toHaveCount(2);
  await page.getByRole('tab', { name: 'Library', exact: true }).click();
  await page.getByText('Create a folder', { exact: true }).click();
  await page.getByLabel('New folder name').fill('Browser tests');
  await page.getByRole('button', { name: 'Create folder', exact: true }).click();
  await page
    .getByRole('button', { name: /Synthetic browser song/ })
    .first()
    .click();
  await page.getByText('Organize song', { exact: true }).click();
  await page.getByLabel('Song name', { exact: true }).fill('Browser organized song');
  await page.getByLabel('Move to folder').selectOption('Browser tests');
  await page.getByRole('button', { name: 'Save organization' }).click();
  await expect(page.getByRole('heading', { name: 'Browser organized song' })).toBeVisible();
  await expect(page.locator('#panel-1 troglodaw-audio canvas').first()).toBeVisible();
  await page.getByRole('button', { name: 'Use as Input Audio', exact: true }).click();
  await expect(page.getByRole('dialog')).toContainText('eight short one-second samples');
  await page.getByRole('button', { name: 'Keep current settings', exact: true }).click();
  await expect(page.locator('.clip-card')).toHaveCount(3);
  const priorAdjustments = page
    .locator('.input-stone .clip-card')
    .last()
    .locator('.clip-adjustments');
  await expect(priorAdjustments).not.toHaveAttribute('open');
  await priorAdjustments.getByText('Clip adjustments', { exact: true }).click();
  await expect(priorAdjustments.getByLabel('Playback speed')).toBeEnabled();
  await page.getByRole('tab', { name: 'Library', exact: true }).click();
  await page.getByRole('button', { name: 'Use as Input Audio', exact: true }).click();
  await expect(page.getByRole('dialog')).not.toBeVisible();
  await page.getByRole('tab', { name: 'Library', exact: true }).click();
  await page.getByRole('button', { name: 'Reuse Creation Ingredients', exact: true }).click();
  await expect(page.getByRole('dialog')).toContainText('unavailable in this saved recipe');
  await page.getByRole('button', { name: 'Reuse selected ingredients' }).click();
  await page.getByRole('tab', { name: 'Library', exact: true }).click();
  await page.getByRole('button', { name: 'Edit Vocal FX', exact: true }).click();
  await expect(page.getByLabel('Voice group', { exact: true })).toBeVisible();
  await expect(page.getByText('Source stems and analysis reused.', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Save FX version', exact: true }).click();
  await expect(page.getByRole('status').filter({ hasText: 'Saved new FX version' })).toBeVisible();
  await page.getByRole('button', { name: 'Save FX version', exact: true }).click();
  await page.getByRole('button', { name: 'Update this FX version', exact: true }).click();
  await expect(page.getByRole('status').filter({ hasText: 'Updated FX version' })).toBeVisible();
  const library = await (await request.get('/api/library')).json();
  expect(library.items.find((item) => item.id === fixture.song.id).name).toBe(
    'Browser organized song',
  );
  expect(library.folders).toContain('Browser tests');
  expect(library.items.filter((item) => item.recipe?.op === 'vocal-fx-song')).toHaveLength(1);
});

test('model storage and missing-model errors use real backend without downloads', async ({
  page,
  request,
}) => {
  await open(page);
  await page.getByRole('button', { name: 'Settings', exact: true }).click();
  const library = await (await request.get('/api/library')).json();
  const destination = library.storage.model_dir + ' with spaces';
  await expect(page.getByLabel('Model storage folder')).toHaveAttribute('readonly');
  if (library.storage.native_folder_picker) {
    await page.route('**/api/storage/pick', (route) =>
      route.fulfill({ json: { path: destination } }),
    );
    await page.getByRole('button', { name: 'Choose model folder…', exact: true }).click();
  } else {
    await page.getByText('Set folder path on this platform', { exact: true }).first().click();
    await page.getByLabel('Manual model folder path').fill(destination);
    await page.getByRole('button', { name: 'Use model folder', exact: true }).click();
  }
  await expect(page.getByRole('status').filter({ hasText: 'Storage updated' })).toBeVisible();
  expect((await (await request.get('/api/library')).json()).storage.model_dir).toBe(destination);
  await page.getByRole('button', { name: 'Set up later', exact: true }).click();
  await page.getByLabel('Input Styles', { exact: true }).fill('folk guitar');
  await page.getByRole('button', { name: 'Generate song', exact: true }).click();
  await expect(page.getByRole('alert').first()).toContainText('Install or verify a music model');
});

test('native folder choices prompt for existing library data and preserve playback after a real move', async ({
  page,
  request,
}) => {
  const fixture = await seed(request);
  let selected = null;
  await page.route('**/api/library', async (route) => {
    const response = await route.fetch();
    const value = await response.json();
    value.storage.native_folder_picker = true;
    await route.fulfill({ response, json: value });
  });
  // Only the OS dialog result is replaced; storage, copying, catalog and media are real.
  await page.route('**/api/storage/pick', (route) => route.fulfill({ json: { path: selected } }));
  await open(page);
  const before = await (await request.get('/api/library')).json();
  await page.getByRole('tab', { name: 'Library', exact: true }).click();
  await page
    .getByRole('button', { name: new RegExp(fixture.song.name) })
    .first()
    .click();
  const player = page.locator('#panel-1 troglodaw-audio').first();
  await expect(player.locator('canvas')).toBeVisible();
  const token = await player.locator('audio').getAttribute('src');
  await page.getByRole('button', { name: 'Settings', exact: true }).click();
  await page.getByText('Library storage', { exact: true }).click();
  await page.getByRole('button', { name: 'Choose library folder…', exact: true }).click();
  await expect(page.getByLabel('Library folder')).toHaveValue(before.storage.library_dir);
  await expect(page.locator('#folder-choice-heading')).toHaveCount(0);
  selected = before.storage.library_dir + ' moved with spaces';
  await page.getByRole('button', { name: 'Choose library folder…', exact: true }).click();
  await expect(page.locator('#folder-choice-heading')).toHaveText('Move existing library data?');
  await expect(page.getByLabel('Library folder')).toHaveValue(before.storage.library_dir);
  await page.getByRole('button', { name: 'Cancel folder change', exact: true }).click();
  expect((await (await request.get('/api/library')).json()).storage.library_dir).toBe(
    before.storage.library_dir,
  );
  await page.getByRole('button', { name: 'Choose library folder…', exact: true }).click();
  await page.getByRole('button', { name: 'Move existing data', exact: true }).click();
  await expect(page.getByLabel('Library folder')).toHaveValue(selected);
  const moved = await (await request.get('/api/library')).json();
  expect(moved.items.some((item) => item.id === fixture.song.id)).toBe(true);
  expect((await request.get(token)).status()).toBe(200);
  await page.getByRole('button', { name: 'Set up later', exact: true }).click();
  await page.reload();
  await expect(page.getByLabel('Library folder')).toHaveValue(selected);
});

test('microphone denial is recoverable and does not discard accepted clips', async ({ page }) => {
  await open(page);
  await page.getByLabel('Add audio files').setInputFiles({
    name: 'accepted.wav',
    mimeType: 'audio/wav',
    buffer: wave(),
  });
  await expect(page.locator('.clip-card')).toHaveCount(1);
  await page.evaluate(() => {
    navigator.mediaDevices.getUserMedia = async () => {
      throw new DOMException('Denied', 'NotAllowedError');
    };
  });
  await page.getByRole('button', { name: 'Record a clip', exact: true }).click();
  await expect(page.getByRole('alert')).toContainText('Microphone access was denied');
  await page.getByRole('button', { name: 'Close dialog', exact: true }).click();
  await expect(page.locator('.clip-card')).toHaveCount(1);
  await page.evaluate(() => {
    navigator.mediaDevices.getUserMedia = async () => {
      throw new DOMException('Missing', 'NotFoundError');
    };
  });
  await page.getByRole('button', { name: 'Record a clip', exact: true }).click();
  await expect(page.getByRole('alert')).toContainText('No microphone is available');
  await page.getByRole('button', { name: 'Close dialog', exact: true }).click();
  await page.evaluate(() => {
    Object.defineProperty(window, 'MediaRecorder', {
      value: undefined,
      configurable: true,
    });
  });
  await page.getByRole('button', { name: 'Record a clip', exact: true }).click();
  await expect(page.getByRole('alert')).toContainText('supported browser on localhost');
  await page.getByRole('button', { name: 'Close dialog', exact: true }).click();
  await expect(page.locator('.clip-card')).toHaveCount(1);
});

test('real browser recording supports keep, discard and individual retakes', async ({
  browser,
}) => {
  const context = await browser.newContext({ permissions: ['microphone'] });
  const page = await context.newPage();
  // Use a synthetic WebAudio stream; no physical microphone is requested.
  await page.addInitScript(() => {
    navigator.mediaDevices.getUserMedia = async () => {
      const audio = new AudioContext();
      const oscillator = audio.createOscillator();
      const output = audio.createMediaStreamDestination();
      oscillator.connect(output);
      oscillator.start();
      const stream = output.stream;
      const stop = stream.getTracks()[0].stop.bind(stream.getTracks()[0]);
      stream.getTracks()[0].stop = () => {
        stop();
        oscillator.stop();
        void audio.close();
      };
      return stream;
    };
  });
  await open(page);
  await page.getByRole('button', { name: 'Record a clip', exact: true }).click();
  await expect(page.getByText('● Recording', { exact: true })).toBeVisible();
  await page.waitForTimeout(900);
  await page.getByRole('button', { name: 'Stop recording', exact: true }).click();
  await page.getByRole('button', { name: 'Keep this take', exact: true }).click();
  await expect(page.locator('.clip-card')).toHaveCount(1);
  const recordedAdjustments = page.locator('.input-stone .clip-card .clip-adjustments');
  await expect(recordedAdjustments).not.toHaveAttribute('open');
  await recordedAdjustments.getByText('Clip adjustments', { exact: true }).click();
  await expect(recordedAdjustments.getByLabel('Playback speed')).toBeEnabled();
  const label = await page.getByLabel('Clip label').inputValue();
  await page.getByRole('button', { name: 'Retake', exact: true }).click();
  await page.waitForTimeout(900);
  await page.getByRole('button', { name: 'Stop recording', exact: true }).click();
  await page.getByRole('button', { name: 'Discard take', exact: true }).click();
  await expect(page.getByLabel('Clip label')).toHaveValue(label);
  await page.getByRole('button', { name: 'Retake', exact: true }).click();
  await page.waitForTimeout(900);
  await page.getByRole('button', { name: 'Stop recording', exact: true }).click();
  await page.getByRole('button', { name: 'Keep this take', exact: true }).click();
  await expect(page.locator('.clip-card')).toHaveCount(1);
  await context.close();
});

test('system appearance, saved override, waveform repaint and accessible themed workflows', async ({
  page,
  request,
}) => {
  await seed(request);
  await page.emulateMedia({ colorScheme: 'dark' });
  await open(page);
  await expect(page).toHaveTitle('TrogloDAW');
  await expect(page.getByRole('heading', { name: 'TrogloDAW', exact: true })).toBeVisible();
  await expect(page.locator('html')).toHaveClass(/dark/);
  await page.getByLabel('Input Styles', { exact: true }).fill('Keep this theme-test draft');
  await page.getByRole('button', { name: 'Light mode', exact: true }).click();
  await page.reload();
  await page.getByRole('button', { name: 'Set up later', exact: true }).click();
  await expect(page.locator('html')).not.toHaveClass(/dark/);
  await expect(page.getByLabel('Input Styles', { exact: true })).toHaveValue(
    'Keep this theme-test draft',
  );
  await page.emulateMedia({ colorScheme: 'light' });
  await page.emulateMedia({ colorScheme: 'dark' });
  await expect(page.locator('html')).not.toHaveClass(/dark/);
  await page.getByRole('button', { name: 'Settings', exact: true }).click();
  await page.getByRole('button', { name: 'Use system theme', exact: true }).click();
  await expect(page.locator('html')).toHaveClass(/dark/);
  await page.getByRole('button', { name: 'Set up later', exact: true }).click();
  await page.emulateMedia({ colorScheme: 'light' });
  await expect(page.locator('html')).not.toHaveClass(/dark/);
  const audit = async () => {
    const result = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
      .analyze();
    expect(
      result.violations.map((v) => ({
        id: v.id,
        nodes: v.nodes.map((n) => n.target),
      })),
    ).toEqual([]);
  };
  for (const theme of ['light', 'dark']) {
    if (theme === 'dark')
      await page.getByRole('button', { name: 'Dark mode', exact: true }).click();
    await page.getByRole('tab', { name: 'Generation', exact: true }).click();
    await audit();
    await page.getByRole('button', { name: 'Settings', exact: true }).click();
    await audit();
    await page.getByRole('button', { name: 'Set up later', exact: true }).click();
    await page.getByRole('tab', { name: 'Library', exact: true }).click();
    await page
      .getByRole('button', { name: /Synthetic browser song/ })
      .first()
      .click();
    await audit();
    await page.getByRole('button', { name: 'Edit Vocal FX', exact: true }).click();
    await expect(page.getByLabel('Voice group', { exact: true })).toBeVisible();
    await audit();
  }
  const canvas = page.locator('#panel-2 canvas').first();
  const darkImage = await canvas.evaluate((el) => el.toDataURL());
  await page.getByRole('button', { name: 'Light mode', exact: true }).click();
  await expect.poll(() => canvas.evaluate((el) => el.toDataURL())).not.toBe(darkImage);
  await page.setViewportSize({ width: 390, height: 844 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);
  await audit();
});

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
      body: JSON.stringify({ detail: 'Synthetic shutdown failure; retry Quit.' }),
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
