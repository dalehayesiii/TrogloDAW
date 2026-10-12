import { describe, expect, it } from 'vitest';
import { NotificationLedger, PresentedJobError, ScopedError, workflow } from './notifications';
import { ProcessingJob } from './job-status';
const job = (id: string, action = 'song_generate', status = 'failed'): ProcessingJob => ({
  id,
  action,
  status,
  message: 'Synthetic failure',
});
function store() {
  const data = new Map<string, string>();
  return {
    getItem: (key: string) => data.get(key) || null,
    setItem: (key: string, value: string) => {
      data.set(key, value);
    },
  };
}
describe('notification acknowledgments', () => {
  it('clears only the attempted workflow and keeps active and future outcomes', () => {
    const ledger = new NotificationLedger(store());
    const jobs = [job('old'), job('fx', 'vocal_render'), job('active', 'song_generate', 'running')];
    ledger.fail('Generation input error', 'song_generate');
    ledger.fail('Lyrics input error', 'lyrics_generate');
    ledger.begin('song_generate', jobs);
    expect(ledger.groups(jobs).map((group) => group.scope)).toEqual(['lyrics', 'vocal-fx']);
    jobs[2].status = 'failed';
    expect(ledger.groups(jobs).find((group) => group.scope === 'generation')?.notices[0].id).toBe(
      'active',
    );
  });
  it('persists manual and retry acknowledgments while preserving the job records', () => {
    const storage = store();
    const ledger = new NotificationLedger(storage);
    const jobs = [job('a'), job('b', 'storage', 'canceled')];
    ledger.dismiss(ledger.groups(jobs)[0].notices[0]);
    ledger.begin('storage', jobs);
    const restored = new NotificationLedger(storage);
    restored.restore(jobs);
    expect(restored.groups(jobs)).toEqual([]);
    expect(jobs.map((item) => item.status)).toEqual(['failed', 'canceled']);
    expect(restored.live.size).toBe(0);
  });
  it('refuses to dismiss active jobs and retains earlier terminal outcomes in one group', () => {
    const ledger = new NotificationLedger(store());
    const active = job('active', 'model_install', 'running');
    ledger.dismiss({ id: active.id, scope: 'model-setup', created: 0, job: active });
    active.status = 'failed';
    expect(ledger.groups([active])[0].notices).toHaveLength(1);
    expect(ledger.groups([job('one'), job('two'), job('three')])).toHaveLength(1);
    expect(ledger.groups([job('one'), job('two'), job('three')])[0].notices).toHaveLength(3);
  });
  it('avoids duplicated represented jobs and preserves ordinary errors across reloads', () => {
    const storage = store();
    const ledger = new NotificationLedger(storage);
    ledger.fail(new PresentedJobError('Already shown'), 'song_generate');
    ledger.fail(new ScopedError(new Error('Transport failed'), 'lyrics'), 'startup');
    ledger.fail(new ScopedError(new Error('Transport failed'), 'lyrics'), 'startup');
    const restored = new NotificationLedger(storage);
    expect(restored.errors).toHaveLength(1);
    expect(restored.errors[0].scope).toBe('lyrics');
    expect(restored.live.size).toBe(0);
    restored.begin('song_generate', []);
    expect(restored.errors).toHaveLength(1);
    restored.begin('lyrics_generate', []);
    expect(restored.errors).toHaveLength(0);
  });
  it('supports blocked/corrupt storage and groups related FX attempts', () => {
    const blocked = new NotificationLedger({
      getItem: () => {
        throw Error('Blocked');
      },
      setItem: () => {
        throw Error('Blocked');
      },
    });
    blocked.fail('Still readable', 'storage');
    expect(blocked.errors).toHaveLength(1);
    const corrupt = new NotificationLedger({ getItem: () => '{broken', setItem: () => {} });
    expect(corrupt.errors).toEqual([]);
    const invalid = new NotificationLedger({
      getItem: () => JSON.stringify({ errors: [null, {}, { id: 1 }] }),
      setItem: () => {},
    });
    expect(invalid.errors).toEqual([]);
    expect(workflow('vocal_prepare')).toBe(workflow('vocal_render'));
    expect(workflow('model_install')).not.toBe(workflow('storage'));
  });
});
