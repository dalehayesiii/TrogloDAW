import { Component, input, output } from '@angular/core';
let nextProgressId = 0;

export interface RemainingRange {
  low: number;
  high: number;
  basis: string;
  samples: number;
}
export interface ProcessingJob {
  id: string;
  action: string;
  status: string;
  message: string;
  stage?: string;
  started_at?: number;
  setup_phase?: string;
  installation_steps_complete?: number;
  installation_steps_total?: number;
  stage_progress?: number | null;
  elapsed_seconds?: number;
  stage_elapsed_seconds?: number;
  runtime_running?: boolean;
  runtime_activity_at?: number;
  queue_wait_seconds?: number;
  queue_remaining?: RemainingRange | null;
  stage_remaining?: RemainingRange | null;
  item_remaining?: RemainingRange | null;
  request_remaining?: RemainingRange | null;
  download_remaining?: RemainingRange | null;
  download_bytes_complete?: number;
  download_bytes_total?: number;
  estimate_state?: string;
  units_complete?: number | null;
  units_total?: number | null;
  item?: number;
  items_complete?: number;
  items_total?: number;
  cancel_requested?: boolean;
  destination?: string;
  asset_name?: string;
  assets_complete?: number;
  assets_total?: number;
  overall_bytes_complete?: number;
  overall_bytes_total?: number;
  downloaded?: number;
  total_bytes?: number;
  resumed_bytes?: number;
}

@Component({
  selector: 'troglodaw-job-status',
  template: `@if (job(); as j) {
    <section class="job processing-card" [attr.aria-label]="title(j.action)">
      <div class="heading-row">
        <span class="section-kicker">{{ title(j.action) }}</span>
        <span class="muted">{{ j.status === 'queued' ? 'Waiting' : j.status }}</span>
      </div>
      <p role="status">{{ j.message }}</p>
      @if (active(j)) {
        @if (j.action === 'model_install') {
          <p class="setup-timing">
            Started {{ started(j.started_at) }} · Download + installation:
            <strong>{{ range(j.request_remaining) }}</strong>
          </p>
          <label [for]="progressId + '-overall'">Overall {{ setupPhase(j) }}</label>
          <progress
            [id]="progressId + '-overall'"
            [attr.value]="setupOverall(j)"
            max="1"
          ></progress>
          <p class="muted">
            {{
              setupPhase(j) === 'download'
                ? range(j.download_remaining)
                : range(j.request_remaining)
            }}
          </p>
          <label [for]="progressId">Current stage {{ setupPhase(j) }}</label>
          <progress [id]="progressId" [attr.value]="j.stage_progress ?? null" max="1"></progress>
          <p class="muted">{{ range(j.stage_remaining) }}</p>
          <p class="muted">Current stage elapsed {{ time(j.stage_elapsed_seconds) }}</p>
          @if (j.runtime_running) {
            <p class="muted">
              Runtime tool is running. New package status may pause during large wheel downloads or
              import checks.
              @if (j.runtime_activity_at) {
                Last package status
                {{ time((DateNow() - j.runtime_activity_at * 1000) / 1000) }} ago.
              }
            </p>
          }
          @if (setupPhase(j) === 'installation' && j.installation_steps_total) {
            <p class="muted">
              {{ j.installation_steps_complete || 0 }} of
              {{ j.installation_steps_total }} verification/runtime checkpoints completed.
              Checkpoints measure completed work, not elapsed time.
            </p>
          }
        } @else {
          <label [for]="progressId">Current stage progress</label>
          <progress [id]="progressId" [attr.value]="j.stage_progress ?? null" max="1"></progress>
        }
        @if (j.units_total && !['downloading', 'verifying'].includes(j.stage || '')) {
          <p class="muted">
            {{ j.units_complete || 0 }} of {{ j.units_total }} {{ unit(j.stage) }}
          </p>
        }
        @if (j.status === 'queued') {
          <p>
            Waiting {{ time(j.queue_wait_seconds) }} · Estimated queue wait:
            {{ range(j.queue_remaining) }}
          </p>
        } @else {
          <p>
            Elapsed {{ time(j.elapsed_seconds) }}
            @if (j.queue_wait_seconds) {
              <span class="muted"> · Waited {{ time(j.queue_wait_seconds) }} in queue</span>
            }
          </p>
          @if (j.action !== 'model_install') {
            <div class="remaining-times">
              <p>
                <span class="muted">This stage</span><strong>{{ range(j.stage_remaining) }}</strong>
              </p>
              @if ((j.items_total || 0) > 1) {
                <p>
                  <span class="muted">Current song</span
                  ><strong>{{ range(j.item_remaining) }}</strong>
                </p>
              }
              <p>
                <span class="muted">Whole request</span
                ><strong>{{ range(j.request_remaining) }}</strong>
              </p>
            </div>
          }
          <p class="muted" [class.notice]="j.estimate_state === 'taking_longer'">
            {{
              j.action === 'model_install' && !j.request_remaining
                ? 'Installation time is still being measured. Download time covers file transfers only; runtime installation and verification follow.'
                : confidence(j.estimate_state)
            }}
          </p>
        }
      } @else {
        <p class="muted">{{ j.status }} · {{ time(j.elapsed_seconds) }} elapsed</p>
      }
      @if (j.items_total) {
        <p>
          {{ j.items_complete || 0 }} of {{ j.items_total }} songs complete
          @if (j.item && active(j)) {
            · Current song {{ j.item }}
          }
        </p>
      }
      @if (j.destination) {
        <p class="storage-destination">
          <span class="muted">Destination:</span> {{ j.destination }}
        </p>
      }
      @if (j.asset_name && active(j) && ['downloading', 'verifying'].includes(j.stage || '')) {
        <p class="muted">{{ j.asset_name }}</p>
      }
      @if (j.download_bytes_total || j.overall_bytes_total) {
        <p>
          Model files present: {{ bytes(j.download_bytes_complete ?? j.overall_bytes_complete) }} /
          {{ bytes(j.download_bytes_total ?? j.overall_bytes_total) }}
          @if (j.assets_total) {
            · {{ j.assets_complete || 0 }} of {{ j.assets_total }} files verified
          }
        </p>
        <p class="muted">
          Runtime installation and verification must also finish before the model is ready.
        </p>
      }
      @if (j.stage === 'downloading' && j.total_bytes) {
        <p>
          Current file: {{ bytes(j.downloaded) }} / {{ bytes(j.total_bytes) }}
          @if (j.resumed_bytes) {
            · Resumed {{ bytes(j.resumed_bytes) }}
          }
        </p>
      }
      @if (active(j)) {
        <button type="button" (click)="cancelRequested.emit()" [disabled]="j.cancel_requested">
          {{ j.cancel_requested ? 'Cancellation requested…' : 'Cancel' }}
        </button>
      }
    </section>
  }`,
})
export class JobStatusComponent {
  DateNow() {
    return Date.now();
  }
  readonly progressId = 'job-progress-' + nextProgressId++;
  readonly job = input.required<ProcessingJob>();
  readonly cancelRequested = output<void>();
  active(job: ProcessingJob) {
    return ['queued', 'running'].includes(job.status);
  }
  time(value = 0) {
    const seconds = Math.max(0, Math.ceil(value));
    return seconds < 60 ? `${seconds}s` : `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
  }
  range(value?: RemainingRange | null) {
    return value ? `${this.time(value.low)}–${this.time(value.high)} remaining` : 'Estimating…';
  }
  bytes(value = 0) {
    return value >= 1024 ** 3
      ? `${(value / 1024 ** 3).toFixed(2)} GiB`
      : `${(value / 1024 ** 2).toFixed(1)} MiB`;
  }
  started(value?: number) {
    return value
      ? new Intl.DateTimeFormat(undefined, { dateStyle: 'short', timeStyle: 'medium' }).format(
          new Date(value * 1000),
        )
      : 'Waiting to start';
  }
  setupPhase(job: ProcessingJob) {
    if (job.setup_phase) return job.setup_phase;
    return job.download_bytes_total && (job.download_bytes_complete || 0) < job.download_bytes_total
      ? 'download'
      : 'installation';
  }
  setupOverall(job: ProcessingJob) {
    const complete =
      this.setupPhase(job) === 'download'
        ? job.download_bytes_complete
        : job.installation_steps_complete;
    const total =
      this.setupPhase(job) === 'download' ? job.download_bytes_total : job.installation_steps_total;
    return total && complete !== undefined ? Math.min(0.99, Math.max(0, complete / total)) : null;
  }
  title(action: string) {
    return (
      (
        {
          song_generate: 'Creating songs',
          vocal_prepare: 'Preparing voices',
          vocal_render: 'Rendering vocal edits',
          model_install: 'Model setup',
          storage: 'Updating storage',
        } as Record<string, string>
      )[action] || 'Processing'
    );
  }
  unit(stage?: string) {
    return (
      (
        {
          generating: 'steps',
          separating: 'chunks',
          identifying: 'voice segments',
          sampling: 'samples',
          rendering: 'segments',
          copying: 'files',
          registering_cache: 'files',
          registering_runtime: 'files',
        } as Record<string, string>
      )[stage || ''] || 'work units'
    );
  }
  confidence(state?: string) {
    return state === 'taking_longer'
      ? 'Taking longer than recent runs. The estimate will adapt as work finishes.'
      : state === 'calibrated'
        ? 'Estimated from recent local runs. Other activity can change the timing.'
        : state === 'stage_calibrated'
          ? 'This stage is estimated from local runs; the full request is still being measured.'
          : state === 'provisional'
            ? 'Provisional estimate from current work; the full request is still being measured.'
            : 'Estimating… Learning this task’s timing.';
  }
}
