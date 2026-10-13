import { ProcessingJob } from './job-status';

export interface ErrorNotice {
  id: string;
  scope: string;
  message: string;
  created: number;
}
export interface Notice<T extends ProcessingJob> {
  id: string;
  scope: string;
  created: number;
  job?: T;
  error?: ErrorNotice;
}
const key = 'troglodaw-notifications-v1';
export function workflow(action: string): string {
  return (
    (
      {
        song_generate: 'generation',
        lyrics_generate: 'lyrics',
        vocal_prepare: 'vocal-fx',
        vocal_render: 'vocal-fx',
        model_install: 'model-setup',
        accept_audio: 'audio-input',
        library_move: 'library',
        library_delete: 'library',
        song_import: 'song-import',
      } as Record<string, string>
    )[action] || action
  );
}
export function workflowLabel(scope: string): string {
  return (
    (
      {
        generation: 'Song generation',
        'song-import': 'Song import',
        lyrics: 'Lyrics',
        'vocal-fx': 'Vocal FX',
        'model-setup': 'Model setup',
        storage: 'Storage',
        'audio-input': 'Input Audio',
        library: 'Library',
        folder: 'Create folder',
        organize: 'Organize song',
        delete: 'Delete song',
        startup: 'Connect to library',
        'setup-close': 'Finish setup',
        updates: 'App updates',
        quit: 'Quit',
      } as Record<string, string>
    )[scope] || scope.replaceAll('_', ' ')
  );
}
export function activeJob(job: ProcessingJob) {
  return ['queued', 'running'].includes(job.status);
}
export class PresentedJobError extends Error {}
export class ScopedError extends Error {
  constructor(
    error: unknown,
    readonly scope: string,
  ) {
    super(error instanceof Error ? error.message : String(error));
  }
}
/** Presentation acknowledgments only; backend jobs/results are never edited. */
export class NotificationLedger {
  errors: ErrorNotice[] = [];
  private dismissed = new Set<string>();
  readonly live = new Set<string>();
  constructor(private readonly storage?: Pick<Storage, 'getItem' | 'setItem'>) {
    try {
      const saved = JSON.parse(storage?.getItem(key) || '{}');
      if (Array.isArray(saved.dismissed))
        this.dismissed = new Set(saved.dismissed.filter((id: unknown) => typeof id === 'string'));
      if (Array.isArray(saved.errors))
        this.errors = saved.errors.filter(
          (e: ErrorNotice) =>
            e &&
            typeof e.id === 'string' &&
            typeof e.scope === 'string' &&
            typeof e.message === 'string' &&
            typeof e.created === 'number' &&
            Number.isFinite(e.created),
        );
    } catch {
      /* Storage may be unavailable or contain a damaged previous value. */
    }
  }
  private save() {
    try {
      this.storage?.setItem(
        key,
        JSON.stringify({ dismissed: [...this.dismissed], errors: this.errors }),
      );
    } catch {
      /* The in-memory lifecycle still works when browser storage is blocked. */
    }
  }
  restore(jobs: ProcessingJob[]) {
    const known = new Set(jobs.map((job) => job.id));
    this.dismissed = new Set([...this.dismissed].filter((id) => known.has(id)));
    this.save();
  }
  begin(action: string, jobs: ProcessingJob[]) {
    const scope = workflow(action);
    for (const job of jobs)
      if (['failed', 'canceled'].includes(job.status) && workflow(job.action) === scope) {
        this.dismissed.add(job.id);
        this.live.delete(job.id);
      }
    this.errors = this.errors.filter((error) => {
      if (error.scope !== scope) return true;
      this.live.delete(error.id);
      return false;
    });
    this.save();
  }
  fail(error: unknown, action: string) {
    if (error instanceof PresentedJobError) return;
    const scope = workflow(error instanceof ScopedError ? error.scope : action);
    const message = error instanceof Error ? error.message : String(error);
    // A repeated transport failure from one observer is one readable notice.
    if (this.errors.some((notice) => notice.scope === scope && notice.message === message)) return;
    const notice = {
      id: crypto.randomUUID(),
      scope,
      message,
      created: Date.now(),
    };
    this.errors.push(notice);
    this.live.add(notice.id);
    this.save();
  }
  dismiss(notice: Notice<ProcessingJob>) {
    if (notice.job && activeJob(notice.job)) return;
    if (notice.job) this.dismissed.add(notice.id);
    else this.errors = this.errors.filter((error) => error.id !== notice.id);
    this.live.delete(notice.id);
    this.save();
  }
  groups<T extends ProcessingJob & { created_at?: number }>(jobs: T[]) {
    const notices: Notice<T>[] = [
      ...jobs
        .filter((job) => ['failed', 'canceled'].includes(job.status) && !this.dismissed.has(job.id))
        .map((job) => ({
          id: job.id,
          scope: workflow(job.action),
          created: (job.created_at || 0) * 1000,
          job,
        })),
      ...this.errors.map((error) => ({
        id: error.id,
        scope: error.scope,
        created: error.created,
        error,
      })),
    ];
    const groups = new Map<string, Notice<T>[]>();
    for (const notice of notices.sort((a, b) => b.created - a.created)) {
      const group = groups.get(notice.scope) || [];
      group.push(notice);
      groups.set(notice.scope, group);
    }
    return [...groups].map(([scope, entries]) => ({
      scope,
      label: workflowLabel(scope),
      notices: entries,
    }));
  }
}
