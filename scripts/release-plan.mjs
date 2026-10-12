import { execFileSync } from 'node:child_process';
import { appendFileSync } from 'node:fs';
import { pathToFileURL } from 'node:url';
import { analyzeCommits } from '@semantic-release/commit-analyzer';
import semver from 'semver';
import { analyzerOptions } from '../config/release.config.mjs';

const git = (...args) => execFileSync('git', args, { encoding: 'utf8' }).trim();
const logger = { log() {}, error() {} };

export async function planRelease(commits, previousVersion) {
  const type = await analyzeCommits(analyzerOptions, { commits, logger, cwd: process.cwd() });
  return type ? (previousVersion ? semver.inc(previousVersion, type) : '1.0.0') : '';
}

export async function main() {
  // Only stable vX.Y.Z tags reachable from HEAD count, matching our sole release branch.
  const tags = git('tag', '--merged', 'HEAD')
    .split('\n')
    .filter((tag) => /^v\d+\.\d+\.\d+$/.test(tag) && semver.valid(tag.slice(1)))
    .sort((a, b) => semver.rcompare(a.slice(1), b.slice(1)));
  const previous = tags[0];
  const range = previous ? `${previous}..HEAD` : 'HEAD';
  const commits = git('log', '--format=%H%x00%B%x00', range)
    .split('\0\n')
    .filter(Boolean)
    .map((entry) => {
      const [hash, message] = entry.trimStart().split('\0');
      return { hash, message };
    });
  const version = await planRelease(commits, previous?.slice(1));
  const output = `version=${version}\nsha=${git('rev-parse', 'HEAD')}\n`;
  if (process.env.GITHUB_OUTPUT) appendFileSync(process.env.GITHUB_OUTPUT, output);
  process.stdout.write(output);
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) await main();
