// Conventional Commits retain semantic-release defaults; docs never release.
export const analyzerOptions = {
  preset: 'conventionalcommits',
  releaseRules: [{ type: 'docs', release: false }],
};

export const notesOptions = {
  preset: 'conventionalcommits',
  presetConfig: {
    types: [
      { type: 'feat', section: 'Features' },
      { type: 'fix', section: 'Fixes' },
      { type: 'perf', section: 'Performance' },
      { type: 'docs', section: 'Documentation', hidden: false },
      { type: 'build', section: 'Build', hidden: false },
      { type: 'ci', section: 'CI', hidden: false },
      { type: 'refactor', section: 'Refactoring', hidden: false },
      { type: 'style', section: 'Style', hidden: false },
      { type: 'test', section: 'Tests', hidden: false },
      { type: 'chore', section: 'Maintenance', hidden: false },
      { type: 'revert', section: 'Reverts', hidden: false },
    ],
  },
};

export default {
  branches: ['main'],
  tagFormat: 'v${version}',
  plugins: [
    ['@semantic-release/commit-analyzer', analyzerOptions],
    ['@semantic-release/release-notes-generator', notesOptions],
    [
      '@semantic-release/exec',
      {
        prepareCmd:
          'python scripts/windows/package.py ${nextRelease.version} && pwsh -File scripts/windows/test_installer.ps1 -ReleaseSmoke',
      },
    ],
    './scripts/release-guard.mjs',
    [
      '@semantic-release/github',
      {
        assets: [
          { path: 'dist/TrogloDAW-Setup.exe', label: 'TrogloDAW Windows x64 installer' },
          { path: 'dist/SHA256SUMS', label: 'Installer SHA-256 checksum' },
          { path: 'dist/release.json', label: 'Build version and source commit' },
        ],
        successComment: false,
        failComment: false,
        releasedLabels: false,
        addReleases: false,
      },
    ],
  ],
};
