// Conventional Commits retain semantic-release defaults; docs never release.
export const analyzerOptions = {
  preset: 'conventionalcommits',
  releaseRules: [{ type: 'docs', release: false }],
};

export default {
  branches: ['main'],
  tagFormat: 'v${version}',
  plugins: [
    ['@semantic-release/commit-analyzer', analyzerOptions],
    ['@semantic-release/release-notes-generator', { preset: 'conventionalcommits' }],
    './scripts/release-guard.mjs',
    [
      '@semantic-release/github',
      {
        assets: [
          { path: 'dist/MusicMaker-Setup.exe', label: 'Windows x64 installer' },
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
