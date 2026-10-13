import { defineConfig } from '@playwright/test';
import { mkdtempSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import { fileURLToPath } from 'node:url';

const testConfig = mkdtempSync(join(tmpdir(), 'troglodaw-config-'));
const testLibrary = mkdtempSync(join(tmpdir(), 'troglodaw-e2e-'));
const testPort = Number(process.env.TROGLODAW_TEST_PORT || 7863);
writeFileSync(
  join(testConfig, 'config.local.json'),
  JSON.stringify({ library_dir: testLibrary, model_dir: join(testConfig, 'models') }),
);

export default defineConfig({
  testDir: '../tests/e2e',
  workers: 1,
  // Quit owns the shared service's final lifecycle; file order must not stop later app tests.
  projects: [
    { name: 'app', testIgnore: '**/shutdown.spec.mjs' },
    { name: 'shutdown', testMatch: '**/shutdown.spec.mjs', dependencies: ['app'] },
  ],
  timeout: 120_000,
  expect: { timeout: 30_000 },
  use: {
    baseURL: `http://127.0.0.1:${testPort}`,
    viewport: { width: 1440, height: 1100 },
    colorScheme: 'light',
    channel: process.env.PLAYWRIGHT_CHANNEL || undefined,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  webServer: {
    command: process.env.TROGLODAW_TEST_PYTHON
      ? `"${process.env.TROGLODAW_TEST_PYTHON}" "${process.env.TROGLODAW_TEST_APP || 'backend/app.py'}" --port ${testPort} --no-browser`
      : `uv run --locked python backend/app.py --port ${testPort} --no-browser`,
    cwd: fileURLToPath(new URL('..', import.meta.url)),
    url: `http://127.0.0.1:${testPort}/api/health`,
    reuseExistingServer: false,
    env: { TROGLODAW_CONFIG_DIR: testConfig, TROGLODAW_LIBRARY: '', TROGLODAW_HOST: '127.0.0.1' },
  },
});
