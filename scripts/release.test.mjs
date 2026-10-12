import assert from 'node:assert/strict';
import { test } from 'node:test';
import { planRelease } from './release-plan.mjs';
import { assertBuild } from './release-guard.mjs';

const commits = (...messages) => messages.map((message) => ({ message, hash: 'test' }));
for (const [message, expected] of [
  ['feat: add stems', '1.3.0'],
  ['fix: repair playback', '1.2.4'],
  ['perf: speed up synthesis', '1.2.4'],
  ['feat!: replace catalog format', '2.0.0'],
  ['fix: change output\n\nBREAKING CHANGE: output is mono', '2.0.0'],
  ['docs: describe installation', ''],
  ['docs!: revise the guide', ''],
  ['docs: rewrite\n\nBREAKING CHANGE: documentation moved', ''],
  ['chore: refresh tooling', ''],
  ['refactor: simplify rendering', ''],
  ['test: cover recipes', ''],
]) {
  test(message, async () => assert.equal(await planRelease(commits(message), '1.2.3'), expected));
}
test('first eligible release starts at 1.0.0', async () => {
  assert.equal(await planRelease(commits('feat: add release tooling')), '1.0.0');
  assert.equal(await planRelease(commits('docs: explain releases')), '');
});
test('documentation does not suppress another pending feature', async () => {
  assert.equal(
    await planRelease(commits('docs: guide', 'fix: repair FX', 'feat: mixer'), '1.2.3'),
    '1.3.0',
  );
});
test('release guard rejects stale or substituted builds', () => {
  const manifest = { version: '1.0.0', sha: 'abc', sha256: '123' };
  assertBuild(manifest, '1.0.0', 'abc', '123');
  for (const args of [
    ['2.0.0', 'abc', '123'],
    ['1.0.0', 'def', '123'],
    ['1.0.0', 'abc', '456'],
  ]) {
    assert.throws(() => assertBuild(manifest, ...args));
  }
});
