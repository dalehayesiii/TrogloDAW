import { expect, test } from '@playwright/test';
import { execFileSync } from 'node:child_process';
import { mkdirSync } from 'node:fs';

function python(requestedCode, library, extra = {}) {
  const code = `import os,sys; from pathlib import Path; sys.path.insert(0,str(Path(os.environ.get('TROGLODAW_TEST_APP','backend/app.py')).resolve().parent)); import troglocore as core; ${requestedCode}`;
  return execFileSync(
    process.env.TROGLODAW_TEST_PYTHON || 'uv',
    process.env.TROGLODAW_TEST_PYTHON ? ['-c', code] : ['run', '--locked', 'python', '-c', code],
    { env: { ...process.env, TROGLODAW_LIBRARY: library, ...extra }, encoding: 'utf8' },
  );
}
async function seed(request, label) {
  const library = (await (await request.get('/api/library')).json()).library;
  const items = JSON.parse(
    python(
      `import json; print(json.dumps([core._new_entry('generated', name, core.synth_voice(1), 'synthetic-bulk-test', recipe={'seed':42}) for name in ['${label} Alpha','${label} Beta','${label} Other']]))`,
      library,
    ),
  );
  return { library, items };
}
async function open(page) {
  const setup = !(await (await page.request.get('/api/library')).json()).storage.setup_seen;
  await page.goto('/');
  const later = page.getByRole('button', { name: 'Set up later', exact: true });
  if (setup) {
    await expect(later).toBeVisible();
    await later.click();
  }
  await page.getByRole('tab', { name: 'Library', exact: true }).click();
}
const panel = (page) => page.locator('#panel-1');
const count = (page, value) =>
  expect(panel(page).locator('.selection-toolbar')).toContainText(`${value} selected`);
async function check(page, name) {
  await selectMode(page);
  await page.getByRole('checkbox', { name: 'Select ' + name, exact: true }).check();
}
async function selectMode(page) {
  const enter = page.getByRole('button', { name: 'Select songs', exact: true });
  if (await enter.isVisible()) await enter.click();
}

test('visible-list selection stays separate from playback and bulk moves preserve recipes', async ({
  page,
  request,
}) => {
  const { items } = await seed(request, 'Scope bulk');
  await open(page);
  await page.getByLabel('Search songs').fill('Scope bulk');
  await check(page, items[0].name);
  await count(page, 1);
  await page.getByRole('button', { name: 'Clear selection', exact: true }).click();
  await count(page, 0);
  await check(page, items[0].name);
  await page.getByRole('tab', { name: 'Generation', exact: true }).click();
  await page.getByRole('tab', { name: 'Library', exact: true }).click();
  await count(page, 1);
  await panel(page)
    .getByRole('button', { name: /Scope bulk Beta/ })
    .click();
  await count(page, 1);
  await expect(panel(page).getByRole('heading', { name: items[1].name })).toBeVisible();
  await expect(panel(page).locator('troglodaw-audio canvas').first()).toBeVisible();
  await page.getByLabel('Search songs').fill('Scope bulk A');
  await count(page, 0);
  await selectMode(page);
  await page.getByRole('button', { name: 'Select page', exact: true }).click();
  await count(page, 1);
  await page.getByLabel('Search songs').fill('Scope bulk');
  await check(page, items[0].name);
  await check(page, items[1].name);
  await page.getByRole('button', { name: 'Move selected…', exact: true }).click();
  await page.getByLabel('Destination folder', { exact: true }).selectOption('__new__');
  await expect(page.getByRole('button', { name: 'Move 2 songs', exact: true })).toBeDisabled();
  await page.getByLabel('New destination folder name').fill('Bulk destination');
  await page.getByRole('button', { name: 'Move 2 songs', exact: true }).click();
  await count(page, 0);
  await expect(page.getByRole('status').filter({ hasText: 'Moved 2 songs' })).toBeVisible();
  await page.reload();
  await page.getByRole('tab', { name: 'Library', exact: true }).click();
  await page.getByLabel('Folder', { exact: true }).selectOption('Bulk destination');
  await expect(panel(page).locator('.song-list li')).toHaveCount(2);
  await selectMode(page);
  await page.getByRole('button', { name: 'Select page', exact: true }).click();
  await count(page, 2);
  await page.getByLabel('Folder', { exact: true }).selectOption('*');
  await count(page, 0);
  const current = (await (await request.get('/api/library')).json()).items;
  for (const original of items.slice(0, 2)) {
    const song = current.find((item) => item.id === original.id);
    expect(song.folder).toBe('Bulk destination');
    expect(song.recipe).toEqual(original.recipe);
    expect(song.path).toBe(original.path);
  }
  expect(current.find((item) => item.id === items[2].id).folder).toBeUndefined();
  await page.getByLabel('Search songs').fill('Scope bulk A');
  await selectMode(page);
  await page.getByRole('button', { name: 'Select page', exact: true }).click();
  await page.getByRole('button', { name: 'Move selected…', exact: true }).click();
  await page.getByLabel('Destination folder', { exact: true }).selectOption('');
  await page.getByRole('button', { name: 'Move 1 song', exact: true }).click();
  await count(page, 0);
  expect(
    (await (await request.get('/api/library')).json()).items.find((i) => i.id === items[0].id)
      .folder,
  ).toBe('');
  await check(page, items[0].name);
  await page.getByRole('button', { name: 'Move selected…', exact: true }).click();
  await page
    .getByLabel('Destination folder', { exact: true })
    .selectOption('folder:Bulk destination');
  await page.getByRole('button', { name: 'Move 1 song', exact: true }).click();
  await count(page, 0);
  expect(
    (await (await request.get('/api/library')).json()).items.find((i) => i.id === items[0].id)
      .folder,
  ).toBe('Bulk destination');
});

test('bulk delete confirms the exact search selection and clears deleted playback', async ({
  page,
  request,
}) => {
  const { items } = await seed(request, 'Delete bulk');
  await open(page);
  await page.getByLabel('Search songs').fill('Delete bulk');
  await panel(page)
    .getByRole('button', { name: /Delete bulk Alpha/ })
    .click();
  await check(page, items[0].name);
  await check(page, items[1].name);
  await page.getByRole('button', { name: 'Delete selected…', exact: true }).click();
  const dialog = page.getByRole('dialog');
  await expect(dialog).toContainText('2 songs selected');
  await expect(dialog).toContainText(items[0].name);
  await expect(dialog).not.toContainText(items[2].name);
  await dialog.getByRole('button', { name: 'Cancel', exact: true }).click();
  await count(page, 2);
  await expect(panel(page).locator('.song-list li')).toHaveCount(3);
  await page.getByRole('button', { name: 'Delete selected…', exact: true }).click();
  await dialog.getByRole('button', { name: 'Delete 2 songs', exact: true }).click();
  await expect(panel(page).locator('.song-list li')).toHaveCount(1);
  await count(page, 0);
  await expect(panel(page).getByRole('heading', { name: items[0].name })).toHaveCount(0);
  await expect(
    panel(page).getByRole('button', { name: 'Use as Input Audio', exact: true }),
  ).toHaveCount(0);
});

test('real partial deletion retains failed selection and retries without duplicate success', async ({
  page,
  request,
}) => {
  const { library, items } = await seed(request, 'Retry bulk');
  const original = items[0].path;
  python(
    "import shutil; original=core.get_item(os.environ['BULK_ID'])['path']; outside=core.LIB.parent/('protected-'+os.environ['BULK_ID']+'.wav'); shutil.copyfile(original,outside); core.update_item(os.environ['BULK_ID'],path=str(outside))",
    library,
    { BULK_ID: items[0].id },
  );
  await open(page);
  await page.getByLabel('Search songs').fill('Retry bulk');
  await check(page, items[0].name);
  await check(page, items[1].name);
  await page.getByRole('button', { name: 'Delete selected…', exact: true }).click();
  await page.getByRole('button', { name: 'Delete 2 songs', exact: true }).click();
  await count(page, 1);
  await expect(
    page.locator('.notice-entry').filter({ hasText: 'outside managed library storage' }),
  ).toContainText('Deleted 1 of 2 songs');
  await expect(
    page.getByRole('checkbox', { name: 'Select ' + items[0].name, exact: true }),
  ).toBeChecked();
  python("core.update_item(os.environ['BULK_ID'],path=os.environ['BULK_PATH'])", library, {
    BULK_ID: items[0].id,
    BULK_PATH: original,
  });
  await page.getByRole('button', { name: 'Delete selected…', exact: true }).click();
  await page.getByRole('button', { name: 'Delete 1 song', exact: true }).click();
  await count(page, 0);
  await expect(
    page.locator('.notice-entry').filter({ hasText: 'outside managed library storage' }),
  ).toHaveCount(0);
  await expect(panel(page).locator('.song-list li')).toHaveCount(1);
});

test('bulk selection and confirmation fit desktop and narrow screens in both themes', async ({
  page,
  request,
}) => {
  const { items } = await seed(request, 'Visual bulk');
  await open(page);
  await page.getByLabel('Search songs').fill('Visual bulk');
  await check(page, items[0].name);
  await check(page, items[1].name);
  const evidence = process.env.TROGLODAW_BULK_EVIDENCE;
  if (evidence) mkdirSync(evidence, { recursive: true });
  for (const theme of ['dark', 'light']) {
    const switchTheme = page.getByRole('button', {
      name: theme === 'dark' ? 'Dark mode' : 'Light mode',
      exact: true,
    });
    if (await switchTheme.isVisible()) await switchTheme.click();
    await expect(page.locator('html')).toHaveAttribute('data-theme', theme);
    for (const width of [1440, 390]) {
      await page.setViewportSize({ width, height: 1000 });
      expect(
        await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth),
      ).toBeTruthy();
      if (evidence)
        await page.screenshot({
          path: evidence + `/library-bulk-${theme}-${width}.png`,
          fullPage: true,
        });
      await page.getByRole('button', { name: 'Delete selected…', exact: true }).click();
      const rect = await page.getByRole('dialog').boundingBox();
      expect(Math.abs(rect.x + rect.width / 2 - width / 2)).toBeLessThan(2);
      expect(rect.width).toBeLessThanOrEqual(width);
      if (evidence)
        await page.screenshot({ path: evidence + `/library-bulk-confirm-${theme}-${width}.png` });
      await page.getByRole('button', { name: 'Cancel', exact: true }).click();
    }
  }
});

test('pagination scopes selection, preserves preview and resets filters and page size', async ({
  page,
  request,
}) => {
  const library = (await (await request.get('/api/library')).json()).library;
  python(
    "[core._new_entry('generated', 'Paged song '+str(n).zfill(2), core.synth_voice(1), 'synthetic-pagination-test') for n in range(25)]",
    library,
  );
  await open(page);
  await page.getByLabel('Search songs').fill('Paged song');
  const rows = panel(page).locator('.song-list li');
  const pages = page.getByRole('navigation', { name: 'Song pages' });
  await expect(rows).toHaveCount(20);
  await expect(pages).toContainText('Showing 1–20 of 25 songs');
  await expect(pages.getByRole('button', { name: 'Previous page' })).toBeDisabled();
  await expect(panel(page).getByRole('checkbox')).toHaveCount(0);
  await expect(panel(page).locator('.selection-toolbar')).toHaveCount(0);
  const previewName = await rows.first().locator('strong').innerText();
  await rows.first().getByRole('button').click();
  await selectMode(page);
  await page.getByRole('button', { name: 'Select page', exact: true }).click();
  await count(page, 20);
  await pages.getByRole('button', { name: 'Next page' }).click();
  await expect(rows).toHaveCount(5);
  await count(page, 0);
  await expect(pages).toContainText('Showing 21–25 of 25 songs');
  await expect(pages.getByRole('button', { name: 'Next page' })).toBeDisabled();
  await expect(panel(page).getByRole('heading', { name: previewName, exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Select page', exact: true }).click();
  await count(page, 5);
  await page.getByRole('button', { name: 'Done selecting', exact: true }).click();
  await expect(panel(page).getByRole('checkbox')).toHaveCount(0);
  await selectMode(page);
  await count(page, 0);
  await page.getByLabel('Search songs').fill(previewName);
  await expect(rows).toHaveCount(1);
  await expect(pages).toContainText('Page 1 of 1');
  await page.getByLabel('Search songs').fill('Paged song');
  await pages.getByRole('button', { name: 'Next page' }).click();
  await page.getByLabel('Songs per page').selectOption({ label: '10' });
  await expect(rows).toHaveCount(10);
  await expect(pages).toContainText('Page 1 of 3');
  await pages.getByRole('button', { name: 'Next page' }).click();
  await page.getByLabel('Folder', { exact: true }).selectOption('');
  await expect(pages).toContainText('Page 1 of 3');
  await page.getByLabel('Songs per page').selectOption({ label: '50' });
  await expect(rows).toHaveCount(25);
  await page.getByLabel('Songs per page').selectOption({ label: '20' });
  const evidence = process.env.TROGLODAW_PAGINATION_EVIDENCE;
  if (evidence) mkdirSync(evidence, { recursive: true });
  for (const theme of ['dark', 'light']) {
    const switchTheme = page.getByRole('button', {
      name: theme === 'dark' ? 'Dark mode' : 'Light mode',
      exact: true,
    });
    if (await switchTheme.isVisible()) await switchTheme.click();
    for (const width of [1440, 390]) {
      await page.setViewportSize({ width, height: 1000 });
      await page.getByRole('button', { name: 'Done selecting', exact: true }).click();
      expect(
        await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth),
      ).toBeTruthy();
      if (evidence)
        await panel(page).screenshot({
          path: evidence + `/library-pagination-browse-${theme}-${width}.png`,
        });
      await selectMode(page);
      await page.getByRole('button', { name: 'Select page', exact: true }).click();
      await count(page, 20);
      if (evidence)
        await panel(page).screenshot({
          path: evidence + `/library-pagination-select-${theme}-${width}.png`,
        });
      await page.getByRole('button', { name: 'Clear selection', exact: true }).click();
    }
  }
  await pages.getByRole('button', { name: 'Next page' }).click();
  await page.getByRole('button', { name: 'Select page', exact: true }).click();
  await page.getByRole('button', { name: 'Delete selected…', exact: true }).click();
  const dialog = page.getByRole('dialog');
  await expect(dialog).toContainText('5 songs selected');
  await dialog.getByRole('button', { name: 'Delete 5 songs', exact: true }).click();
  await expect(rows).toHaveCount(20);
  await expect(pages).toContainText('Showing 1–20 of 20 songs');
  await expect(pages).toContainText('Page 1 of 1');
  await count(page, 0);
  expect(
    (await (await request.get('/api/library')).json()).items.filter((item) =>
      item.name.startsWith('Paged song'),
    ).length,
  ).toBe(20);
  await page.reload();
  await page.getByRole('tab', { name: 'Library', exact: true }).click();
  await expect(panel(page).getByRole('checkbox')).toHaveCount(0);
});
