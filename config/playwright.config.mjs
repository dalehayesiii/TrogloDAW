import { defineConfig } from '@playwright/test';
import { mkdtempSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import { fileURLToPath } from 'node:url';

const testConfig = mkdtempSync(join(tmpdir(), 'musicmaker-config-'));
const testLibrary = mkdtempSync(join(tmpdir(), 'musicmaker-e2e-'));
writeFileSync(
  join(testConfig, 'config.local.json'),
  JSON.stringify({ library_dir: testLibrary, model_dir: join(testConfig, 'models') }),
);

export default defineConfig({
  testDir: '../tests/e2e',
  workers: 1,
  timeout: 120_000,
  expect: { timeout: 30_000 },
  use: {
    baseURL: 'http://127.0.0.1:7863',
    viewport: { width: 1440, height: 1100 },
    colorScheme: 'light',
    channel: process.env.PLAYWRIGHT_CHANNEL || undefined,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  webServer: {
    command: process.env.MM_TEST_PYTHON
      ? `"${process.env.MM_TEST_PYTHON}" "${process.env.MM_TEST_APP || 'backend/app.py'}" --port 7863 --no-browser`
      : 'uv run --locked python backend/app.py --port 7863 --no-browser',
    cwd: fileURLToPath(new URL('..', import.meta.url)),
    url: 'http://127.0.0.1:7863/api/health',
    reuseExistingServer: false,
    env: { MM_CONFIG_DIR: testConfig, MM_LIBRARY: '', MM_HOST: '127.0.0.1' },
  },
});
