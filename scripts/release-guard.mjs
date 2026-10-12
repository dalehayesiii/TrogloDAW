import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { readFileSync, readdirSync } from 'node:fs';

export function assertBuild(manifest, version, sha, checksum) {
  if (manifest.version !== version || manifest.sha !== sha || manifest.sha256 !== checksum) {
    throw new Error(
      'Release version, source commit, or installer checksum differs from the tested build.',
    );
  }
}

export function assertDistribution(manifest, checksum, sums, installers = [manifest.installer]) {
  const installer = `TrogloDAW-Setup-${manifest.version}.exe`;
  if (
    !/^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$/.test(manifest.version) ||
    manifest.installer !== installer
  ) {
    throw new Error('Release manifest does not identify the canonical installer.');
  }
  if (sums.trim() !== `${checksum}  ${installer}`) {
    throw new Error('Published checksum file differs from the canonical installer.');
  }
  if (installers.length !== 1 || installers[0] !== installer) {
    throw new Error('Release upload must contain exactly the versioned installer.');
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
    .update(readFileSync(`dist/TrogloDAW-Setup-${nextRelease.version}.exe`))
    .digest('hex');
  const manifest = JSON.parse(readFileSync('dist/release.json', 'utf8'));
  assertBuild(manifest, nextRelease.version, sha, checksum);
  assertDistribution(
    manifest,
    checksum,
    readFileSync('dist/SHA256SUMS', 'utf8'),
    readdirSync('dist').filter(
      (name) => name.startsWith('TrogloDAW-Setup-') && name.endsWith('.exe'),
    ),
  );
}
