import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';

export function assertBuild(manifest, version, sha, checksum) {
  if (manifest.version !== version || manifest.sha !== sha || manifest.sha256 !== checksum) {
    throw new Error(
      'Release version, source commit, or installer checksum differs from the tested build.',
    );
  }
}

export function assertAliases(checksum, legacyChecksum, sums) {
  if (legacyChecksum !== checksum)
    throw new Error('Legacy installer alias differs from TrogloDAW installer.');
  if (sums.trim() !== `${checksum}  TrogloDAW-Setup.exe\n${checksum}  MusicMaker-Setup.exe`) {
    throw new Error('Published checksum file differs from the installer aliases.');
  }
}

// semantic-release runs prepare BEFORE creating its tag or publishing its release.
export async function prepare(_config, { nextRelease }) {
  const sha = execFileSync('git', ['rev-parse', 'HEAD'], { encoding: 'utf8' }).trim();
  if (process.env.GITHUB_REF !== 'refs/heads/main' || process.env.GITHUB_SHA !== sha) {
    throw new Error('Releases must run on the tested main push.');
  }
  const latest = execFileSync('git', ['ls-remote', 'origin', 'refs/heads/main'], {
    encoding: 'utf8',
  }).split(/\s/)[0];
  if (latest !== sha)
    throw new Error('main advanced during the build; release the newer tested commit instead.');
  const checksum = createHash('sha256')
    .update(readFileSync('dist/TrogloDAW-Setup.exe'))
    .digest('hex');
  const manifest = JSON.parse(readFileSync('dist/release.json', 'utf8'));
  assertBuild(manifest, nextRelease.version, sha, checksum);
  const legacyChecksum = createHash('sha256')
    .update(readFileSync('dist/MusicMaker-Setup.exe'))
    .digest('hex');
  assertAliases(checksum, legacyChecksum, readFileSync('dist/SHA256SUMS', 'utf8'));
}
