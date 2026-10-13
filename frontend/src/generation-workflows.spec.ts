import { TestBed } from '@angular/core/testing';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { AppComponent } from './app';

describe('Generation workflow boundaries', () => {
  beforeEach(() => {
    localStorage.removeItem('troglodaw-generation-draft');
    localStorage.removeItem('troglodaw-workflow-drafts');
    vi.stubGlobal('matchMedia', () => ({ matches: false, addEventListener() {} }));
    vi.spyOn(AppComponent.prototype, 'initialize').mockResolvedValue();
    vi.spyOn(AppComponent.prototype, 'hydrateClips').mockResolvedValue();
  });
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
    localStorage.removeItem('troglodaw-generation-draft');
    localStorage.removeItem('troglodaw-workflow-drafts');
  });

  it('preserves independent recording/model/backing drafts across switching and reload', async () => {
    const app = TestBed.createComponent(AppComponent).componentInstance;
    app.draft.lyrics = 'Keep these literal words';
    app.draft.styles = 'dry spoken voice';
    app.draft.audio_mode = 'postmix';
    app.draft.clips = [
      { key: 'prior', id: 'prior', label: 'Prior', source_type: 'prior-song', settings: {} },
    ];
    app.switchGenerationWorkflow('recording-style');
    expect(app.draft.clips).toEqual([]);
    expect(app.draft.lyrics).toBe('');
    app.draft.clips = [
      { key: 'take', id: 'take', label: 'Take', source_type: 'microphone', settings: {} },
    ];
    app.draft.styles = 'warm acoustic';
    app.switchGenerationWorkflow('arrange-over-song');
    app.draft.backing_song_id = 'backing';
    app.switchGenerationWorkflow('model');
    expect(app.draft.lyrics).toBe('Keep these literal words');
    expect(app.draft.audio_mode).toBe('postmix');
    expect(app.draft.clips[0].id).toBe('prior');
    await Promise.resolve();
    const reloaded = TestBed.createComponent(AppComponent).componentInstance;
    reloaded.switchGenerationWorkflow('recording-style');
    expect(reloaded.draft.styles).toBe('warm acoustic');
    expect(reloaded.draft.clips[0].id).toBe('take');
    reloaded.switchGenerationWorkflow('arrange-over-song');
    expect(reloaded.draft.backing_song_id).toBe('backing');
  });

  it('submits only applicable recording inputs without changing the stored draft', () => {
    const app = TestBed.createComponent(AppComponent).componentInstance;
    app.switchGenerationWorkflow('recording-style');
    app.draft.styles = 'folk';
    app.draft.lyrics = 'Inactive stored words';
    app.draft.backing_song_id = 'inactive-backing';
    app.draft.arrangement = { samples: ['inactive'] };
    app.draft.clips = [
      { key: 'take', id: 'take', label: 'Take', source_type: 'upload', settings: { pitch: 12 } },
    ];
    const original = structuredClone(app.draft);
    const request = app.generationRequest();
    expect(request.lyrics).toBeUndefined();
    expect(request.backing_song_id).toBeUndefined();
    expect(request.arrangement).toBeUndefined();
    expect(request.clips[0].settings).toEqual({});
    expect(request.options.duration).toBeUndefined();
    expect(request.audio_mode).toBe('conditioned');
    expect(app.draft).toEqual(original);
  });

  it('defaults fresh sampled drafts to conditioning and preserves an explicit saved postmix', () => {
    const fresh = TestBed.createComponent(AppComponent).componentInstance;
    expect(fresh.draft.audio_mode).toBe('conditioned');
    localStorage.setItem('troglodaw-generation-draft', JSON.stringify({ audio_mode: 'postmix' }));
    expect(TestBed.createComponent(AppComponent).componentInstance.draft.audio_mode).toBe(
      'postmix',
    );
  });

  it('selectively reuses a workflow without overwriting the draft being left', async () => {
    const app = TestBed.createComponent(AppComponent).componentInstance;
    app.draft.lyrics = 'Saved sampled words';
    app.switchGenerationWorkflow('recording-style');
    app.draft.styles = 'Intact take style';
    app.reference = { available: { workflow: 'model', styles: 'Recipe style' } } as any;
    app.referenceFields = { workflow: true, styles: true };
    app.applyReference();
    expect(app.draft.lyrics).toBe('Saved sampled words');
    expect(app.draft.styles).toBe('Recipe style');
    await Promise.resolve();
    app.switchGenerationWorkflow('recording-style');
    expect(app.draft.styles).toBe('Intact take style');
  });
});
