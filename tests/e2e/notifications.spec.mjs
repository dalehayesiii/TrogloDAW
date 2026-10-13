import { expect, test } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
const headers = { 'X-TrogloDAW-Request': '1' };
async function failure(request, action, values = {}) {
  const response = await request.post('/api/jobs', { headers, data: { action, values } });
  expect(response.ok()).toBe(true);
  const { id } = await response.json();
  await expect
    .poll(async () => (await (await request.get('/api/jobs/' + id)).json()).status)
    .toBe('failed');
  return id;
}
async function open(page) {
  const setup = !(await (await page.request.get('/api/library')).json()).storage.setup_seen;
  await page.goto('/');
  if (setup) await page.getByRole('button', { name: 'Set up later', exact: true }).click();
  await expect(page.getByRole('dialog')).not.toBeVisible();
  await expect(page.getByRole('tab').first()).toBeVisible();
}
test('persistent failures group, dismiss, survive reload and clear only on relevant retry', async ({
  page,
  request,
}) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  const first = await failure(request, 'folder');
  const second = await failure(request, 'folder');
  const generation = await failure(request, 'song_generate', {
    clips: [],
    lyrics: 'Synthetic test',
    count: 1,
    options: { duration: '999' },
  });
  await open(page);
  const folders = page.getByRole('region', { name: 'Create folder notifications', exact: true });
  const songs = page.getByRole('region', { name: 'Song generation notifications', exact: true });
  await expect(folders.locator('.processing-card:visible')).toHaveCount(1);
  await expect(folders.getByText('1 earlier Create folder notice')).toBeVisible();
  await expect(page.getByRole('alert')).toHaveCount(0); // Restored history is not a new announcement.
  await folders.getByText('1 earlier Create folder notice').click();
  await expect(folders.locator('.processing-card:visible')).toHaveCount(2);
  await folders.getByRole('button', { name: 'Dismiss Creating folder notice' }).first().click();
  await expect(folders.locator('.processing-card')).toHaveCount(1);
  await page.reload();
  await expect(folders.locator('.processing-card')).toHaveCount(1);
  await expect(songs).toBeVisible();
  await page.getByRole('tab', { name: 'Library', exact: true }).click();
  await page.getByText('Create a folder', { exact: true }).click();
  await page.getByRole('button', { name: 'Create folder', exact: true }).click();
  await expect(folders.getByRole('alert')).toContainText('Choose a folder name');
  await expect(folders.locator('.processing-card')).toHaveCount(1);
  await expect(page.locator('.persistent-error')).toHaveCount(0); // No global duplicate.
  await page.waitForTimeout(8200);
  await expect(folders.getByRole('alert')).toBeVisible();
  await expect(songs).toBeVisible();
  await page.getByLabel('New folder name').fill('Recovered notification test');
  await page.getByRole('button', { name: 'Create folder', exact: true }).click();
  await expect(folders).toHaveCount(0);
  await expect(songs).toBeVisible();
  // Retry acknowledges old failures immediately; reload only after the new request succeeds.
  await expect(page.getByLabel('Notification', { exact: true })).toContainText('Folder created');
  await page.reload();
  await expect(folders).toHaveCount(0);
  await expect(page.getByLabel('Notification', { exact: true })).toHaveCount(0);
  for (const id of [first, second, generation])
    expect((await (await request.get('/api/jobs/' + id)).json()).status).toBe('failed');
  await page.getByRole('button', { name: 'Settings', exact: true }).click();
  const dialog = page.getByRole('dialog');
  await expect(dialog.getByRole('region', { name: 'Song generation notifications' })).toBeVisible();
  for (const theme of ['light', 'dark']) {
    await page.emulateMedia({ colorScheme: theme, reducedMotion: 'reduce' });
    await expect(page.locator('html')).toHaveAttribute('data-theme', theme);
    await page.setViewportSize({ width: 390, height: 844 });
    await expect(page.locator('html')).toHaveAttribute('data-theme', theme);
    await dialog
      .getByRole('button', { name: 'Dismiss Creating songs notice' })
      .evaluate(async (button) => {
        await Promise.all(
          button.getAnimations().map((animation) => animation.finished.catch(() => {})),
        );
      });
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(
      390,
    );
    expect(
      (await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze())
        .violations,
    ).toEqual([]);
  }
  await dialog.getByRole('button', { name: 'Dismiss Creating songs notice' }).click();
  await expect(dialog.getByRole('region', { name: 'Song generation notifications' })).toHaveCount(
    0,
  );
  await page.reload();
  await expect(page.getByRole('region', { name: 'Song generation notifications' })).toHaveCount(0);
});
test('ordinary recording errors persist, dismiss manually and retry without clearing unrelated errors', async ({
  page,
  request,
}) => {
  await failure(request, 'folder');
  await open(page);
  await page.evaluate(() => {
    navigator.mediaDevices.getUserMedia = async () => {
      throw new DOMException('Denied', 'NotAllowedError');
    };
  });
  await page.getByRole('button', { name: 'Record a clip', exact: true }).click();
  const dialog = page.getByRole('dialog');
  await expect(dialog.getByRole('alert')).toContainText('Microphone access was denied');
  await page.reload();
  const recording = page.getByRole('region', { name: 'Input Audio notifications' });
  await expect(recording).toContainText('Microphone access was denied');
  await expect(recording.getByRole('alert')).toHaveCount(0);
  await page.evaluate(() => {
    navigator.mediaDevices.getUserMedia = async () => {
      throw new DOMException('Denied again', 'NotAllowedError');
    };
  });
  await page.getByRole('button', { name: 'Record a clip', exact: true }).click();
  await expect(recording.getByRole('alert')).toContainText('Microphone access was denied');
  await expect(recording.locator('.persistent-error')).toHaveCount(1);
  await expect(page.getByRole('region', { name: 'Create folder notifications' })).toBeVisible();
  await recording.getByRole('button', { name: 'Dismiss error' }).click();
  await page.reload();
  await expect(recording).toHaveCount(0);
  await expect(page.getByRole('region', { name: 'Create folder notifications' })).toBeVisible();
});
