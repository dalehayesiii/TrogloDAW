import { expect, test } from '@playwright/test';
import { execFileSync } from 'node:child_process';

const headers = { 'X-TrogloDAW-Request': '1' };
async function open(page) {
  const setup = !(await (await page.request.get('/api/library')).json()).storage.setup_seen;
  await page.goto('/');
  if (setup) await page.getByRole('button', { name: 'Set up later', exact: true }).click();
  await expect(page.getByRole('tab').first()).toBeVisible();
}
async function seed(request) {
  const library = await (await request.get('/api/library')).json();
  return JSON.parse(
    execFileSync(
      process.env.TROGLODAW_TEST_PYTHON || 'uv',
      process.env.TROGLODAW_TEST_PYTHON
        ? ['scripts/seed_browser_fixture.py']
        : ['run', '--locked', 'python', 'scripts/seed_browser_fixture.py'],
      { env: { ...process.env, TROGLODAW_LIBRARY: library.library }, encoding: 'utf8' },
    ),
  );
}
async function rename(request, id, name) {
  const response = await request.post('/api/jobs', {
    headers,
    data: { action: 'organize', values: { id, name, folder: '' } },
  });
  const job = await response.json();
  await expect
    .poll(async () => (await (await request.get('/api/jobs/' + job.id)).json()).status)
    .toBe('complete');
}

test('latest Library selection owns loading, audio and failure recovery', async ({
  page,
  request,
}) => {
  const a = await seed(request);
  const b = await seed(request);
  await rename(request, a.song.id, 'Slow preview song');
  await rename(request, b.song.id, 'Latest preview song');
  await open(page);
  await page.getByRole('tab', { name: 'Library', exact: true }).click();
  const panel = page.locator('#panel-1');
  let release;
  const gate = new Promise((resolve) => (release = resolve));
  let slowStarted = false;
  let expectedUrl;
  await page.route('**/api/items/' + a.song.id, async (route) => {
    const response = await route.fetch();
    slowStarted = true;
    await gate;
    await route.fulfill({ response });
  });
  await page.route('**/api/items/' + b.song.id, async (route) => {
    const response = await route.fetch();
    expectedUrl = (await response.json()).audio.url;
    await route.fulfill({ response });
  });
  await panel.locator('.song-row').filter({ hasText: 'Slow preview song' }).click();
  await expect.poll(() => slowStarted).toBe(true);
  await expect(panel.getByText('Loading song preview…', { exact: true })).toBeVisible();
  await expect(panel.locator('.playback-stone .audio-controls')).toHaveCount(0);
  await panel.locator('.song-row').filter({ hasText: 'Latest preview song' }).click();
  await expect.poll(() => expectedUrl).toBeTruthy();
  await expect(panel.locator('.playback-stone audio').first()).toHaveAttribute('src', expectedUrl);
  const slowResponse = page.waitForResponse('**/api/items/' + a.song.id);
  release();
  await slowResponse;
  await expect(
    panel.getByRole('heading', { name: 'Latest preview song', exact: true }),
  ).toBeVisible();
  await expect(panel.locator('.playback-stone audio').first()).toHaveAttribute('src', expectedUrl);
  await page.unroute('**/api/items/' + a.song.id);
  let fail = true;
  await page.route('**/api/items/' + a.song.id, (route) =>
    fail
      ? route.fulfill({ status: 503, json: { detail: 'Synthetic preview failure' } })
      : route.continue(),
  );
  await panel.locator('.song-row').filter({ hasText: 'Slow preview song' }).click();
  await expect(panel.getByText(/Could not load this song preview/)).toBeVisible();
  await expect(page.getByRole('alert')).toContainText('Synthetic preview failure');
  await expect(panel.locator('.playback-stone .audio-controls')).toHaveCount(0);
  fail = false;
  await panel.getByRole('button', { name: 'Retry preview', exact: true }).click();
  await expect(
    panel.getByRole('button', { name: 'Play Slow preview song', exact: true }),
  ).toBeVisible();
  await expect(panel.getByText(/Could not load this song preview/)).toHaveCount(0);
  await expect(page.getByRole('alert')).toHaveCount(0);
  // Deleting A must not clear a newer selection made while deletion is pending.
  let releaseDelete;
  let deleting = false;
  const deleteGate = new Promise((resolve) => (releaseDelete = resolve));
  await page.route('**/api/jobs', async (route) => {
    if (route.request().method() !== 'POST' || route.request().postDataJSON().action !== 'delete')
      return route.continue();
    deleting = true;
    await deleteGate;
    await route.continue();
  });
  await panel.getByText('Organize song', { exact: true }).click();
  page.once('dialog', (dialog) => dialog.accept());
  await panel.getByRole('button', { name: 'Delete song', exact: true }).click();
  await expect.poll(() => deleting).toBe(true);
  await panel.locator('.song-row').filter({ hasText: 'Latest preview song' }).click();
  releaseDelete();
  await expect
    .poll(async () =>
      (await (await request.get('/api/library')).json()).items.some(
        (item) => item.id === a.song.id,
      ),
    )
    .toBe(false);
  await expect(
    panel.getByRole('heading', { name: 'Latest preview song', exact: true }),
  ).toBeVisible();
  await expect(
    panel.getByRole('button', { name: 'Play Latest preview song', exact: true }),
  ).toBeVisible();
  // Bulk deletion refresh must also invalidate an in-flight preview of its removed song.
  await page.unroute('**/api/items/' + b.song.id);
  let releaseRemoved;
  let removedStarted = false;
  const removedGate = new Promise((resolve) => (releaseRemoved = resolve));
  await page.route('**/api/items/' + b.song.id, async (route) => {
    const response = await route.fetch();
    removedStarted = true;
    await removedGate;
    await route.fulfill({ response });
  });
  await panel.locator('.song-row').filter({ hasText: 'Latest preview song' }).click();
  await expect.poll(() => removedStarted).toBe(true);
  await panel.getByRole('checkbox', { name: 'Select Latest preview song', exact: true }).check();
  await panel.getByRole('button', { name: 'Delete selected…', exact: true }).click();
  await page
    .getByRole('dialog')
    .getByRole('button', { name: 'Delete 1 song', exact: true })
    .click();
  await expect(panel.locator('.playback-stone')).toHaveCount(0);
  const removedResponse = page.waitForResponse('**/api/items/' + b.song.id);
  releaseRemoved();
  await removedResponse;
  await expect(panel.locator('.playback-stone')).toHaveCount(0);
});

test('audio controls explain mute, failures and source changes without the club action', async ({
  page,
  request,
}) => {
  const fixture = await seed(request);
  const other = await seed(request);
  await rename(request, fixture.song.id, 'Player feedback song');
  await rename(request, other.song.id, 'Replacement player song');
  await open(page);
  await page.getByRole('tab', { name: 'Library', exact: true }).click();
  const panel = page.locator('#panel-1');
  await panel.locator('.song-row').filter({ hasText: 'Player feedback song' }).click();
  const player = panel.locator('.playback-stone troglodaw-audio').first();
  await player.getByRole('button', { name: 'Mute Player feedback song', exact: true }).click();
  await expect(
    player.getByRole('button', { name: 'Unmute Player feedback song', exact: true }),
  ).toHaveClass(/muted-audio/);
  expect(await player.locator('audio').evaluate((audio) => audio.muted)).toBe(true);
  await player.getByLabel('Playback speed', { exact: true }).selectOption('2');
  expect(await player.locator('audio').evaluate((audio) => audio.playbackRate)).toBe(2);
  await expect(player.locator('.audio-share')).toHaveCount(0);
  await expect(
    player.getByRole('link', { name: 'Download Player feedback song', exact: true }),
  ).toBeVisible();
  await player.locator('audio').evaluate((audio) => {
    audio.play = async () => {
      throw new Error('Synthetic playback denial');
    };
  });
  await player.getByRole('button', { name: 'Play Player feedback song', exact: true }).click();
  await expect(player.getByText(/Could not play this audio.*download the file/)).toBeVisible();
  // Keep the same component while changing its media, not just a newly mounted player.
  await panel.locator('.song-row').filter({ hasText: 'Replacement player song' }).click();
  await expect(player.getByLabel('Playback speed', { exact: true })).toHaveValue('1');
  await expect(
    player.getByRole('button', { name: 'Mute Replacement player song', exact: true }),
  ).toBeVisible();
  expect(
    await player
      .locator('audio')
      .evaluate((audio) => ({ rate: audio.playbackRate, muted: audio.muted })),
  ).toEqual({ rate: 1, muted: false });
  await expect(player.locator('.audio-feedback')).toHaveCount(0);
});

test('search and empty pickers offer the relevant next step', async ({ page }) => {
  const actual = await (await page.request.get('/api/library')).json();
  await page.route('**/api/library', (route) =>
    route.fulfill({ json: { ...actual, items: [], folders: [] } }),
  );
  await open(page);
  await page.getByRole('button', { name: 'Choose from Library', exact: true }).click();
  await expect(page.getByRole('dialog')).toContainText(
    'No saved audio yet. Upload a file or record a clip',
  );
  await page
    .getByRole('dialog')
    .getByRole('button', { name: 'Go to Generation', exact: true })
    .click();
  await page.getByRole('button', { name: /^Prior Song Reference/ }).click();
  await expect(page.getByRole('dialog')).toContainText('No songs to reference yet');
  await page.getByRole('button', { name: 'Close dialog', exact: true }).click();
  await page.unroute('**/api/library');
  await page.getByRole('button', { name: 'Refresh library', exact: true }).click();
  await page.getByRole('tab', { name: 'Library', exact: true }).click();
  await page.getByLabel('Search songs', { exact: true }).fill('Missing synthetic song xyz');
  await expect(
    page.locator('#panel-1 .empty-state').filter({ hasText: 'No songs match' }),
  ).toBeVisible();
  await page.getByRole('button', { name: 'Clear search and filters', exact: true }).click();
  await expect(page.getByLabel('Search songs', { exact: true })).toHaveValue('');
  await expect(page.getByLabel('Folder', { exact: true })).toHaveValue('*');
});

test('invalid generation counts are explained before submitting any job', async ({ page }) => {
  await page.route('**/api/library', async (route) => {
    const actual = await (await route.fetch()).json();
    await route.fulfill({
      json: { ...actual, models: { ...actual.models, ready: true, planner: { ready: true } } },
    });
  });
  let submissions = 0;
  await page.route('**/api/jobs', (route) => {
    if (route.request().method() === 'POST') submissions++;
    return route.continue();
  });
  await open(page);
  for (const value of ['', '0', '33', '1.5']) {
    await page.getByLabel('Number of Generations', { exact: true }).fill(value);
    await expect(
      page.getByText('Enter a whole number from 1 to 32.', { exact: true }),
    ).toBeVisible();
    await page.getByRole('button', { name: /^Generate songs?$/ }).click();
    await expect(page.getByLabel('Number of Generations', { exact: true })).toBeFocused();
  }
  expect(submissions).toBe(0);
  await page.getByLabel('Number of Generations', { exact: true }).fill('3');
  await expect(page.locator('#generation-count-error')).toBeEmpty();
  await page.reload();
  await expect(page.getByRole('button', { name: 'Settings', exact: true })).toBeEnabled();
  await expect(page.getByLabel('Number of Generations', { exact: true })).toHaveValue('3');
  await page.unrouteAll({ behavior: 'wait' });
});

test('FX distinguishes original and rendered audio when controls change during a render', async ({
  page,
  request,
}) => {
  const fixture = await seed(request);
  await rename(request, fixture.song.id, 'FX provenance song');
  await open(page);
  await page.getByRole('tab', { name: 'Library', exact: true }).click();
  await page.locator('#panel-1 .song-row').filter({ hasText: 'FX provenance song' }).click();
  await page.getByRole('button', { name: 'Edit Vocal FX', exact: true }).click();
  const panel = page.locator('#panel-2');
  await expect(page.getByRole('button', { name: 'Preview remix', exact: true })).toBeVisible();
  await expect(panel.getByText(/Saved song audio/)).toBeVisible();
  await page.getByRole('button', { name: 'Preview remix', exact: true }).click();
  await expect(panel.getByRole('button', { name: 'Play FX remix', exact: true })).toBeVisible();
  await page.getByLabel('Gain (dB) value', { exact: true }).fill('-6');
  await expect(panel.getByText(/This is the last rendered remix/)).toBeVisible();
  await expect(
    panel.getByRole('button', { name: 'Play Last rendered FX remix', exact: true }),
  ).toBeVisible();
  let release;
  const gate = new Promise((resolve) => (release = resolve));
  let started = false;
  await page.route('**/api/jobs', async (route) => {
    if (
      route.request().method() !== 'POST' ||
      route.request().postDataJSON().action !== 'vocal_render'
    )
      return route.continue();
    started = true;
    await gate;
    await route.continue();
  });
  await page.getByRole('button', { name: 'Preview remix', exact: true }).click();
  await expect.poll(() => started).toBe(true);
  await page.getByLabel('Gain (dB) value', { exact: true }).fill('-12');
  release();
  await expect(page.getByRole('button', { name: 'Preview remix', exact: true })).toBeEnabled();
  await expect(panel.getByText(/This is the last rendered remix/)).toBeVisible();
  await page.unroute('**/api/jobs');
  await page.getByRole('button', { name: 'Preview remix', exact: true }).click();
  await expect(panel.getByRole('button', { name: 'Play FX remix', exact: true })).toBeVisible();
  await expect(panel.getByText(/This is the last rendered remix/)).toHaveCount(0);
});

test('long song names leave audio actions clickable at desktop and narrow widths', async ({
  page,
  request,
}) => {
  const fixture = await seed(request);
  const name = 'LongSongName'.repeat(10);
  await rename(request, fixture.song.id, name);
  await open(page);
  await page.getByRole('tab', { name: 'Library', exact: true }).click();
  await page.locator('#panel-1 .song-row').filter({ hasText: name }).click();
  const player = page.locator('#panel-1 .playback-stone troglodaw-audio').first();
  await expect(player.locator('canvas')).toBeVisible();
  for (const theme of ['light', 'dark']) {
    if ((await page.locator('html').getAttribute('data-theme')) !== theme)
      await page
        .getByRole('button', { name: theme === 'dark' ? 'Dark mode' : 'Light mode', exact: true })
        .click();
    for (const width of [1440, 390]) {
      await page.setViewportSize({ width, height: 900 });
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(
        true,
      );
      for (const action of [
        player.locator('.audio-download'),
        player.locator('.audio-controls > button'),
      ]) {
        const box = await action.boundingBox();
        expect(box.width).toBeGreaterThanOrEqual(32);
        expect(box.height).toBeGreaterThanOrEqual(32);
        await action.click({ trial: true });
      }
      const label = await player.locator('.corner-label').boundingBox();
      const download = await player.locator('.audio-download').boundingBox();
      expect(label.x + label.width).toBeLessThanOrEqual(download.x);
    }
  }
});

test('folder actions have space and success toasts center on the page and in dialogs', async ({
  page,
}, testInfo) => {
  await open(page);
  await page.getByRole('tab', { name: 'Library', exact: true }).click();
  await page.getByText('Create a folder', { exact: true }).click();
  for (const theme of ['light', 'dark']) {
    if ((await page.locator('html').getAttribute('data-theme')) !== theme)
      await page
        .getByRole('button', { name: theme === 'dark' ? 'Dark mode' : 'Light mode', exact: true })
        .click();
    for (const width of [1440, 390]) {
      await page.setViewportSize({ width, height: 900 });
      const input = page.getByLabel('New folder name', { exact: true });
      const button = page.getByRole('button', { name: 'Create folder', exact: true });
      const fieldBox = await input.boundingBox();
      const actionBox = await button.boundingBox();
      expect(actionBox.y - fieldBox.y - fieldBox.height).toBeGreaterThanOrEqual(12);
      await input.fill(`Toast review ${theme} ${width}`);
      await button.click();
      const toast = page.getByLabel('Notification', { exact: true });
      await expect(toast).toBeVisible();
      const pageToast = await toast.boundingBox();
      expect(Math.abs(pageToast.x + pageToast.width / 2 - width / 2)).toBeLessThanOrEqual(1);
      expect(pageToast.x).toBeGreaterThanOrEqual(0);
      expect(pageToast.x + pageToast.width).toBeLessThanOrEqual(width);
      await page.screenshot({ path: testInfo.outputPath(`folder-toast-${theme}-${width}.png`) });
      await page.getByRole('button', { name: 'Settings', exact: true }).click();
      const dialog = page.getByRole('dialog');
      await expect(dialog.getByLabel('Notification', { exact: true })).toBeVisible();
      const dialogBox = await dialog.boundingBox();
      const dialogToast = await toast.boundingBox();
      expect(
        Math.abs(dialogToast.x + dialogToast.width / 2 - dialogBox.x - dialogBox.width / 2),
      ).toBeLessThanOrEqual(1);
      expect(dialogToast.x).toBeGreaterThanOrEqual(dialogBox.x);
      expect(dialogToast.x + dialogToast.width).toBeLessThanOrEqual(dialogBox.x + dialogBox.width);
      await page.screenshot({ path: testInfo.outputPath(`dialog-toast-${theme}-${width}.png`) });
      await dialog.getByRole('button', { name: 'Close dialog', exact: true }).click();
      await toast.getByRole('button', { name: 'Dismiss notification', exact: true }).click();
      await expect(toast).toHaveCount(0);
    }
  }
});

test('setup and Settings identify writing and voice models separately from readiness', async ({
  page,
}, testInfo) => {
  let firstRun = true;
  let ready = false;
  await page.route('**/api/library', async (route) => {
    const actual = await (await route.fetch()).json();
    await route.fulfill({
      json: {
        ...actual,
        storage: { ...actual.storage, setup_seen: !firstRun },
        models: { ...actual.models, ready, planner: { ...actual.models.planner, ready } },
      },
    });
  });
  await page.goto('/');
  const dialog = page.getByRole('dialog');
  await expect(
    dialog.getByRole('heading', { name: 'Welcome to TrogloDAW', exact: true }),
  ).toBeVisible();
  await expect(dialog.getByText('Qwen3 0.6B', { exact: true })).toBeVisible();
  await expect(dialog.getByText('ACE-Step 5Hz LM 1.7B', { exact: true })).toBeVisible();
  firstRun = false;
  await dialog.getByRole('button', { name: 'Set up later', exact: true }).click();
  for (const installed of [false, true]) {
    ready = installed;
    await page.reload();
    await expect(page.getByRole('button', { name: 'Settings', exact: true })).toBeEnabled();
    for (const theme of ['light', 'dark']) {
      if ((await page.locator('html').getAttribute('data-theme')) !== theme)
        await page
          .getByRole('button', { name: theme === 'dark' ? 'Dark mode' : 'Light mode', exact: true })
          .click();
      for (const width of [1440, 390]) {
        await page.setViewportSize({ width, height: 900 });
        await page.getByRole('button', { name: 'Settings', exact: true }).click();
        await expect(dialog.getByText('Lyric writing model', { exact: true })).toBeVisible();
        await expect(dialog.getByText('Qwen3 0.6B', { exact: true })).toBeVisible();
        await expect(
          dialog.getByText('Automatic song length model', { exact: true }),
        ).toBeVisible();
        await expect(dialog.getByText('ACE-Step 5Hz LM 1.7B', { exact: true })).toBeVisible();
        await expect(
          dialog.getByText(
            new RegExp(`Optional song writing tools: ${installed ? 'ready' : 'not installed'}`),
          ),
        ).toBeVisible();
        const voice = dialog.locator('.voice-models');
        await expect(voice).not.toHaveAttribute('open');
        await voice.getByText('Voice processing models', { exact: true }).click();
        await expect(voice.getByText('HDemucs High', { exact: true })).toBeVisible();
        await expect(voice.getByText('SpeechBrain ECAPA-TDNN', { exact: true })).toBeVisible();
        await dialog.getByText('Qwen3 0.6B', { exact: true }).scrollIntoViewIfNeeded();
        expect(await dialog.evaluate((element) => element.scrollWidth <= element.clientWidth)).toBe(
          true,
        );
        await page.screenshot({
          path: testInfo.outputPath(`model-roles-${installed}-${theme}-${width}.png`),
        });
        await voice.getByText('Voice processing models', { exact: true }).click();
        await dialog.getByRole('button', { name: 'Close dialog', exact: true }).click();
      }
    }
  }
  await page.unrouteAll({ behavior: 'wait' });
});
