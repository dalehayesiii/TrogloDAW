import assert from 'node:assert/strict';
import { test } from 'node:test';
import { analyzeCommits } from '@semantic-release/commit-analyzer';
import { generateNotes } from '@semantic-release/release-notes-generator';
import { analyzerOptions, notesOptions } from '../config/release.config.mjs';
import { assertBuild, assertAliases } from './release-guard.mjs';

const logger = { log() {}, error() {} };
const commits = (...messages) =>
  messages.map((message, index) => ({ message, hash: String(index + 1).padStart(40, '0') }));
test('docs never trigger a release, including breaking descriptions', async () => {
  for (const message of [
    'docs: explain releases',
    'docs!: change docs',
    'docs: guide\n\nBREAKING CHANGE: guide moved',
  ]) {
    assert.equal(
      await analyzeCommits(analyzerOptions, { commits: commits(message), logger }),
      null,
    );
  }
});
test('documentation does not suppress another pending feature', async () => {
  assert.equal(
    await analyzeCommits(analyzerOptions, {
      commits: commits('docs: guide', 'fix: repair FX', 'feat: mixer'),
      logger,
    }),
    'minor',
  );
});
test('release notes cover maintenance and code changes between release tags', async () => {
  const types = notesOptions.presetConfig.types.map(({ type }) => type);
  const notes = await generateNotes(notesOptions, {
    cwd: process.cwd(),
    logger,
    options: { repositoryUrl: 'https://github.com/dalehayesiii/music-maker' },
    commits: commits(...types.map((type) => `${type}: change for ${type}`)),
    lastRelease: { version: '1.2.3', gitTag: 'v1.2.3' },
    nextRelease: { version: '1.3.0', gitTag: 'v1.3.0' },
  });
  for (const type of types) assert.ok(notes.includes(`change for ${type}`), type);
  assert.ok(notes.includes('/compare/v1.2.3...v1.3.0'));
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
test('branded installer and legacy alias must share the published checksum', () => {
  const sums = 'abc  TrogloDAW-Setup.exe\nabc  MusicMaker-Setup.exe\n';
  assertAliases('abc', 'abc', sums);
  assert.throws(() => assertAliases('abc', 'different', sums));
  assert.throws(() => assertAliases('abc', 'abc', 'abc  MusicMaker-Setup.exe\n'));
});
