import { TestBed } from '@angular/core/testing';
import { describe, expect, it } from 'vitest';
import { JobStatusComponent, ProcessingJob } from './job-status';

const job: ProcessingJob = {
  id: 'demo',
  action: 'song_generate',
  status: 'running',
  message: 'Loading local model',
  elapsed_seconds: 12,
  stage_progress: null,
  estimate_state: 'estimating',
};

describe('honest processing status', () => {
  it('separates all-file transfer time from verification and complete setup', async () => {
    const fixture = TestBed.createComponent(JobStatusComponent);
    const transfer = {
      ...job,
      action: 'model_install',
      stage: 'downloading',
      message: 'Downloading weights',
      destination: 'D:/models',
      download_bytes_complete: 1024 ** 3,
      download_bytes_total: 6 * 1024 ** 3,
      download_remaining: { low: 300, high: 420, samples: 4, basis: 'live_units' },
      assets_complete: 2,
      assets_total: 24,
      started_at: new Date('2026-10-12T12:00:00Z').getTime() / 1000,
    };
    fixture.componentRef.setInput('job', transfer);
    await fixture.whenStable();
    expect(fixture.nativeElement.textContent).toContain('Overall download');
    expect(fixture.nativeElement.textContent).toContain(
      'Started ' + fixture.componentInstance.started(transfer.started_at),
    );
    expect(fixture.nativeElement.querySelectorAll('progress')).toHaveLength(2);
    expect(fixture.nativeElement.querySelector('progress').value).toBeCloseTo(1 / 6);
    expect(fixture.nativeElement.textContent).toContain('5m 0s–7m 0s remaining');
    expect(fixture.nativeElement.textContent).toContain('D:/models');
    expect(fixture.nativeElement.textContent).toContain('1.00 GiB / 6.00 GiB');
    expect(fixture.nativeElement.textContent).toContain('2 of 24 files verified');
    expect(fixture.nativeElement.textContent).toContain('must also finish');
    fixture.componentRef.setInput('job', {
      ...transfer,
      stage: 'installing',
      setup_phase: 'installation',
      installation_steps_complete: 24,
      installation_steps_total: 29,
      download_bytes_complete: 6 * 1024 ** 3,
      download_remaining: null,
    });
    await fixture.whenStable();
    expect(fixture.nativeElement.textContent).not.toContain('Overall download');
    expect(fixture.nativeElement.textContent).toContain('Overall installation');
    expect(fixture.nativeElement.textContent).toContain('24 of 29');
    expect(fixture.nativeElement.querySelector('progress').value).toBeCloseTo(24 / 29);
    expect(fixture.nativeElement.querySelectorAll('progress')[1].hasAttribute('value')).toBe(false);
    expect(fixture.nativeElement.textContent).not.toContain('Whole request');
    expect(fixture.nativeElement.textContent).toContain('Estimating…');
  });

  it('keeps unknown work indeterminate and clears active estimates at cancellation', async () => {
    const fixture = TestBed.createComponent(JobStatusComponent);
    fixture.componentRef.setInput('job', job);
    await fixture.whenStable();
    expect(fixture.nativeElement.querySelector('progress').hasAttribute('value')).toBe(false);
    expect(fixture.nativeElement.textContent).toContain('Estimating…');
    expect(fixture.nativeElement.textContent).toContain('Elapsed 12s');
    fixture.componentRef.setInput('job', {
      ...job,
      status: 'canceled',
      elapsed_seconds: 17,
      estimate_state: 'finished',
    });
    await fixture.whenStable();
    expect(fixture.nativeElement.querySelector('progress')).toBeNull();
    expect(fixture.nativeElement.textContent).toContain('17s elapsed');
    expect(fixture.nativeElement.textContent).not.toContain('remaining');
  });

  it('shows stage, current song and whole request ranges with sequential counts', async () => {
    const fixture = TestBed.createComponent(JobStatusComponent);
    const range = { low: 60, high: 90, samples: 3, basis: 'local_history' };
    fixture.componentRef.setInput('job', {
      ...job,
      stage: 'generating',
      stage_progress: 0.5,
      units_complete: 16,
      units_total: 32,
      item: 2,
      items_complete: 1,
      items_total: 3,
      stage_remaining: range,
      item_remaining: range,
      request_remaining: { ...range, high: 180 },
      estimate_state: 'calibrated',
    });
    await fixture.whenStable();
    expect(fixture.nativeElement.querySelector('progress').value).toBe(0.5);
    expect(fixture.nativeElement.textContent).toContain('16 of 32 steps');
    expect(fixture.nativeElement.textContent).toContain('1 of 3 songs complete');
    expect(fixture.nativeElement.textContent).toContain('Current song 2');
    expect(fixture.nativeElement.textContent).toContain('1m 0s–3m 0s remaining');
    expect(fixture.nativeElement.textContent).toContain('recent local runs');
  });

  it('uses distinct progress labels across dialogs and disables repeat cancellation', async () => {
    const first = TestBed.createComponent(JobStatusComponent),
      second = TestBed.createComponent(JobStatusComponent);
    first.componentRef.setInput('job', job);
    second.componentRef.setInput('job', { ...job, cancel_requested: true });
    await first.whenStable();
    await second.whenStable();
    expect(first.nativeElement.querySelector('progress').id).not.toBe(
      second.nativeElement.querySelector('progress').id,
    );
    let calls = 0;
    first.componentInstance.cancelRequested.subscribe(() => calls++);
    first.nativeElement.querySelector('button').click();
    expect(calls).toBe(1);
    expect(second.nativeElement.querySelector('button').disabled).toBe(true);
  });
});
