import {
  ChangeDetectorRef,
  Component,
  ElementRef,
  HostListener,
  ViewChild,
  inject,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { NgTemplateOutlet } from '@angular/common';
import { AudioComponent, DownloadComponent, Field, FieldComponent, Media, Value } from './controls';
import { JobStatusComponent, ProcessingJob } from './job-status';
import {
  NotificationLedger,
  Notice,
  PresentedJobError,
  ScopedError,
  workflow,
} from './notifications';

interface Clip {
  key: string;
  id: string;
  label: string;
  source_type: string;
  audio?: Media;
  preset?: 'apply' | 'keep';
  settings: Record<string, number>;
  saved_file?: string;
}
interface Draft {
  clips: Clip[];
  lyrics: string;
  lyric_idea: string;
  lyric_language: string;
  styles: string;
  title: string;
  count: number;
  options: Record<string, Value>;
  audio_mode: 'conditioned' | 'postmix';
  audio_adherence: number;
  arrangement?: any;
}
interface Item {
  id: string;
  name: string;
  type: string;
  duration: number;
  folder?: string;
  recipe?: any;
  source_type?: string;
}
interface Job extends ProcessingJob {
  id: string;
  action: string;
  status: string;
  message: string;
  progress: number;
  result?: any;
  song_id?: string;
  [key: string]: any;
}
const defaults = (): Draft => ({
  clips: [],
  lyrics: '',
  lyric_idea: '',
  lyric_language: 'en',
  styles: '',
  title: '',
  count: 2,
  audio_mode: 'conditioned',
  audio_adherence: 75,
  options: {
    gender: '',
    duration: 'auto',
    weirdness: 50,
    influence: 50,
    variety: 0,
  },
});
const field = (
  key: string,
  label: string,
  kind: Field['kind'],
  initial: Value,
  min?: number,
  max?: number,
  step?: number,
  choices?: string[],
): Field => ({ key, label, kind, initial, min, max, step, choices });
export const fxFields: Field[] = [
  field('pitch', 'Pitch (semitones)', 'slider', 0, -12, 12, 0.5),
  field('stretch', 'Time stretch (fixed timeline slot)', 'slider', 1, 0.5, 2, 0.05),
  field('gain', 'Gain (dB)', 'slider', 0, -24, 24, 0.5),
  field('low_cut', 'Low cut / high-pass Hz (0=off)', 'slider', 0, 0, 1000, 10),
  field('high_cut', 'High cut / low-pass Hz (0=off)', 'slider', 0, 0, 20000, 100),
  field('compress', 'Compression', 'check', false),
  field('comp_threshold', 'Comp threshold dB', 'slider', -20, -60, 0, 1),
  field('comp_ratio', 'Comp ratio', 'slider', 4, 1, 20, 0.5),
  field('chorus', 'Chorus mix', 'slider', 0, 0, 1, 0.05),
  field('robot', 'Robot mix', 'slider', 0, 0, 1, 0.05),
  field('robot_hz', 'Robot pitch Hz', 'slider', 110, 40, 400, 5),
  field('delay', 'Echo mix', 'slider', 0, 0, 1, 0.05),
  field('delay_time', 'Echo time s', 'slider', 0.3, 0.05, 1.5, 0.05),
  field('delay_feedback', 'Echo feedback', 'slider', 0.35, 0, 0.9, 0.05),
  field('reverb', 'Reverb wet', 'slider', 0, 0, 1, 0.05),
  field('room_size', 'Room size', 'slider', 0.6, 0, 1, 0.05),
  field('trim', 'Trim silence without shifting timing', 'check', false),
  field('trim_db', 'Trim threshold below peak (dB)', 'slider', 40, 10, 80, 1),
  field('normalize', 'Normalize this voice group', 'check', false),
];

@Component({
  selector: 'troglodaw-app',
  imports: [
    FormsModule,
    NgTemplateOutlet,
    AudioComponent,
    DownloadComponent,
    FieldComponent,
    JobStatusComponent,
  ],
  templateUrl: './app.html',
})
export class AppComponent {
  private cdr = inject(ChangeDetectorRef);
  @ViewChild('dialog') dialog?: ElementRef<HTMLDialogElement>;
  tabs = ['Generation', 'Library', 'Vocal FX'];
  tab = 0;
  draft = defaults();
  audioImports = 0;
  get audioConditioningSupported() {
    const model = this.library.models;
    return model.choices.some(
      (choice: any) => choice.id === model.selected && choice.conditioning?.includes('cover'),
    );
  }
  library: any = {
    items: [],
    folders: [],
    storage: {},
    models: { choices: [], ready: false },
  };
  jobs: Job[] = [];
  results: any[] = [];
  notices = new NotificationLedger(
    (() => {
      try {
        return localStorage;
      } catch {
        return undefined;
      }
    })(),
  );
  status = '';
  private statusTimer?: ReturnType<typeof setTimeout>;
  stopped = false;
  quitting = false;
  update: any = {
    phase: 'idle',
    version: '0.0.0',
    supported: false,
    message: 'Loading update status…',
  };
  updateToken = '';
  updateHandoff = false;
  private updateTimer?: ReturnType<typeof setTimeout>;
  private captureTimer?: ReturnType<typeof setInterval>;
  private captureClient = crypto.randomUUID();
  dialogKind = '';
  selectedSong = '';
  checkedSongs = new Set<string>();
  bulkSongs: Item[] = [];
  bulkFolder = '';
  bulkNewFolder = '';
  bulkSubmitting = false;
  libraryAudio: Media | null = null;
  libraryLoading = false;
  libraryPreviewError = '';
  private librarySelection = 0;
  libraryAssets: { label: string; media: Media | null }[] = [];
  get selectedRecipe() {
    return JSON.stringify(this.selected?.recipe, null, 2);
  }
  search = '';
  folderFilter = '*';
  newFolder = '';
  songName = '';
  songFolder = '';
  libraryPath = '';
  modelPath = '';
  modelChoice = 'acestep-v15-base';
  choosingFolder = false;
  folderChoice: {
    kind: 'library' | 'model';
    path: string;
    from: string;
  } | null = null;
  presetClip?: Clip;
  reference: any = null;
  referenceFields: Record<string, boolean> = {};
  fx: any = null;
  fxSongId = '';
  fxGroup = '';
  fxName = '';
  fxPreview: Media | null = null;
  private fxPreviewSettings = '';
  get fxSettings() {
    return JSON.stringify({
      groups: this.fx?.groups.map((group: any) => [group.id, group.settings]),
      segments: this.fx?.segments,
    });
  }
  get fxPreviewStale() {
    return !!this.fxPreview && this.fxPreviewSettings !== this.fxSettings;
  }
  get generationCountError() {
    return Number.isInteger(this.draft.count) && this.draft.count >= 1 && this.draft.count <= 32
      ? ''
      : 'Enter a whole number from 1 to 32.';
  }
  capture?: MediaStream;
  recorder?: MediaRecorder;
  recording = false;
  requestingMic = false;
  inputHelp = false;
  private micSession = 0;
  take?: File;
  takeUrl = '';
  retakeIndex = -1;
  theme = 'light';
  appearance = 'system';
  private systemAppearance = window.matchMedia('(prefers-color-scheme: dark)');
  fxFields = fxFields;
  generationFields = [
    field('gender', 'Vocal Gender', 'select', '', undefined, undefined, undefined, [
      '',
      'Male',
      'Female',
    ]),
    field('duration', 'Duration (auto or 10–300 seconds)', 'text', 'auto'),
    field('weirdness', 'Weirdness — Safe to Chaos', 'slider', 50, 0, 100, 1),
    field('influence', 'Style Influence — Loose to Strong', 'slider', 50, 0, 100, 1),
    field('variety', 'Variety — vary the styles, keep your lyrics', 'slider', 0, 0, 100, 1),
  ];
  private polling = new Set<string>();
  constructor() {
    try {
      this.appearance = localStorage.getItem('troglodaw-theme') || 'system';
    } catch {}
    if (!['light', 'dark', 'system'].includes(this.appearance)) this.appearance = 'system';
    this.applyAppearance();
    this.systemAppearance.addEventListener('change', () => {
      if (this.appearance === 'system') this.applyAppearance();
    });
    try {
      this.draft = {
        ...defaults(),
        ...JSON.parse(localStorage.getItem('troglodaw-generation-draft') || '{}'),
      };
    } catch {
      this.draft = defaults();
    }
    if (!Array.isArray(this.draft.clips)) this.draft.clips = [];
    this.draft.options = { ...defaults().options, ...this.draft.options };
    void this.initialize();
  }
  async initialize() {
    try {
      await this.refresh();
      this.jobs = (await this.api('/api/jobs')).jobs;
      this.notices.restore(this.jobs);
      for (const job of this.jobs) {
        if (this.active(job)) void this.poll(job.id).catch((error) => this.fail(error, job.action));
        else if (job.status === 'complete') this.receive(job, false);
      }
      await this.hydrateClips();
      if (!this.library.storage.setup_seen) this.openDialog('setup');
      void this.refreshUpdates();
    } catch (error) {
      this.fail(error, 'startup');
    }
  }
  async api(path: string, body?: any) {
    const response = await fetch(
      path,
      body === undefined
        ? {}
        : {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'X-TrogloDAW-Request': '1',
            },
            body: JSON.stringify(body),
          },
    );
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || 'Request failed');
    return data;
  }
  get notificationGroups() {
    return this.notices.groups(this.jobs);
  }
  get activeJobs() {
    return this.jobs.filter((job) => this.active(job));
  }
  beginWorkflow(action: string) {
    this.notices.begin(action, this.jobs);
    this.cdr.markForCheck();
  }
  fail(error: unknown, action = 'startup') {
    this.notices.fail(error, action);
    this.cdr.markForCheck();
  }
  dismissNotice(notice: Notice<Job>) {
    const focused = document.activeElement?.closest('.notice-entry');
    this.notices.dismiss(notice);
    this.cdr.detectChanges();
    if (focused && !document.contains(focused)) {
      const target = this.dialogKind
        ? this.dialog?.nativeElement.querySelector<HTMLButtonElement>('button')
        : document.getElementById('tab-' + this.tab);
      target?.focus();
    }
  }
  notify(message: string) {
    this.dismissStatus();
    this.status = message;
    this.statusTimer = setTimeout(() => this.dismissStatus(), 8000);
    this.cdr.markForCheck();
  }
  dismissStatus() {
    if (this.statusTimer) clearTimeout(this.statusTimer);
    this.statusTimer = undefined;
    this.status = '';
    this.cdr.markForCheck();
  }
  async refreshLibrary() {
    this.beginWorkflow('startup');
    this.beginWorkflow('library');
    try {
      await this.refresh();
    } catch (error) {
      this.fail(error, 'startup');
    }
  }
  async refresh() {
    this.library = await this.api('/api/library');
    const shown = new Set(this.filteredSongs.map((song) => song.id));
    this.checkedSongs = new Set([...this.checkedSongs].filter((id) => shown.has(id)));
    if (this.selectedSong && !this.selected) {
      this.librarySelection++;
      this.libraryLoading = false;
      this.libraryPreviewError = '';
      this.selectedSong = '';
      this.libraryAudio = null;
      this.libraryAssets = [];
    }
    if (!['storage', 'setup'].includes(this.dialogKind) || !this.libraryPath || !this.modelPath) {
      this.libraryPath = this.library.storage.library_dir;
      this.modelPath = this.library.storage.model_dir;
      this.modelChoice = this.library.models.selected;
    }
    this.cdr.markForCheck();
  }
  saveDraft() {
    queueMicrotask(() =>
      localStorage.setItem('troglodaw-generation-draft', JSON.stringify(this.draft)),
    );
  }
  active(job: Job) {
    return ['queued', 'running'].includes(job.status);
  }
  get busy() {
    return (
      this.bulkSubmitting ||
      this.audioImports > 0 ||
      this.jobs.some((job) => this.active(job) && job.action !== 'model_install')
    );
  }
  get installingModel() {
    return this.jobs.some((job) => job.action === 'model_install' && this.active(job));
  }
  get storageBusy() {
    return this.busy || this.installingModel;
  }
  get songs(): Item[] {
    return this.library.items.filter((item: Item) => ['generated', 'mix'].includes(item.type));
  }
  get filteredSongs() {
    return this.songs.filter(
      (item) =>
        (this.folderFilter === '*' || (item.folder || '') === this.folderFilter) &&
        item.name.toLowerCase().includes(this.search.toLowerCase()),
    );
  }
  get selected(): Item | undefined {
    return this.songs.find((item) => item.id === this.selectedSong);
  }
  toggleSong(id: string, checked: boolean) {
    if (checked) this.checkedSongs.add(id);
    else this.checkedSongs.delete(id);
  }
  clearSongSelection() {
    this.checkedSongs = new Set();
  }
  selectAllShown() {
    this.checkedSongs = new Set(this.filteredSongs.map((song) => song.id));
  }
  openBulk(kind: 'bulk-move' | 'bulk-delete') {
    if (this.busy) return;
    this.bulkSongs = this.filteredSongs.filter((song) => this.checkedSongs.has(song.id));
    if (!this.bulkSongs.length) return;
    this.bulkFolder = '';
    this.bulkNewFolder = '';
    this.openDialog(kind);
  }
  async runBulk() {
    if (
      this.busy ||
      !this.bulkSongs.length ||
      !['bulk-move', 'bulk-delete'].includes(this.dialogKind)
    )
      return;
    const action = this.dialogKind === 'bulk-move' ? 'library_move' : 'library_delete';
    const values = {
      ids: this.bulkSongs.map((song) => song.id),
      folder: this.bulkFolder === '__new__' ? this.bulkNewFolder : this.bulkFolder.slice(7),
      create_folder: this.bulkFolder === '__new__',
    };
    this.bulkSubmitting = true;
    this.closeDialog();
    try {
      await this.submit(action, values);
    } catch (error) {
      this.fail(error, 'library');
    } finally {
      this.bulkSubmitting = false;
      this.cdr.markForCheck();
    }
  }
  get currentGroup(): any {
    return this.fx?.groups?.find((group: any) => group.id === this.fxGroup);
  }
  get referenceKeys(): string[] {
    return Object.keys(this.reference?.available || {});
  }
  async submit(action: string, values: any): Promise<Job> {
    this.beginWorkflow(action);
    try {
      const created = await this.api('/api/jobs', { action, values });
      return await this.poll(created.id);
    } catch (error) {
      if (error instanceof PresentedJobError) throw error;
      throw new ScopedError(error, workflow(action));
    }
  }
  async poll(id: string): Promise<Job> {
    if (this.polling.has(id)) throw new Error('Already following this job');
    this.polling.add(id);
    try {
      for (;;) {
        const state: Job = await this.api('/api/jobs/' + id);
        const index = this.jobs.findIndex((job) => job.id === id);
        if (index >= 0) this.jobs[index] = state;
        else this.jobs.push(state);
        if (state.action === 'song_generate' && state.outcomes) this.results = state.outcomes;
        this.cdr.markForCheck();
        if (!this.active(state)) {
          this.notices.live.add(state.id);
          this.receive(state);
          await this.refresh();
          if (['failed', 'canceled'].includes(state.status))
            throw new PresentedJobError(state.message);
          return state;
        }
        await new Promise((resolve) => setTimeout(resolve, 500));
      }
    } finally {
      this.polling.delete(id);
    }
  }
  receive(job: Job, announce = true) {
    const result = job.result;
    if (!result) return;
    if (announce && ['library_move', 'library_delete'].includes(job.action)) {
      for (const id of result.completed_ids || []) this.checkedSongs.delete(id);
      if (job.action === 'library_move' && result.completed_ids?.includes(this.selectedSong))
        this.songFolder = result.folder;
      if (result.problems?.length) {
        this.fail(new Error(result.message + '. ' + result.problems.join('; ')), 'library');
        return;
      }
    }
    if (job.action === 'song_generate') this.results = result.outcomes || [];
    if (job.status !== 'complete') return;
    if (announce && job.action === 'lyrics_generate') {
      this.draft.lyrics = result.lyrics;
      this.saveDraft();
    }
    if (job.action === 'vocal_prepare' && job.song_id === this.fxSongId) {
      const previous = this.fx?.song?.id === result.song.id ? this.fx.groups : [];
      for (const group of result.groups) {
        const existing = previous.find((entry: any) => entry.id === group.id);
        if (existing) group.settings = existing.settings;
      }
      this.fx = result;
      this.fxGroup = result.groups.some((group: any) => group.id === this.fxGroup)
        ? this.fxGroup
        : result.groups[0]?.id || '';
      this.fxName = result.song.name + (result.song.recipe?.op === 'vocal-fx-song' ? '' : '_FX');
    }
    if (job.action === 'vocal_render' && job.song_id === this.fxSongId) {
      this.fxPreview = result.audio;
      if (result.song && this.fx) {
        this.fx.song = result.song;
        this.fxSongId = result.song.id;
      }
    }
    if (announce && result.message) this.notify(result.message);
    this.cdr.markForCheck();
  }
  async cancel(job: Job) {
    try {
      await this.api('/api/jobs/' + job.id + '/cancel', {});
    } catch (error) {
      this.fail(error, job.action);
    }
  }
  changeTab(index: number) {
    this.stopCapture();
    this.tab = index;
    this.saveDraft();
  }
  tabKey(event: KeyboardEvent, index: number) {
    const next =
      event.key === 'ArrowRight'
        ? (index + 1) % 3
        : event.key === 'ArrowLeft'
          ? (index + 2) % 3
          : event.key === 'Home'
            ? 0
            : event.key === 'End'
              ? 2
              : -1;
    if (next >= 0) {
      event.preventDefault();
      this.changeTab(next);
      document.getElementById('tab-' + next)?.focus();
    }
  }
  openDialog(kind: string) {
    if (['storage', 'setup'].includes(kind) && !this.library.storage.library_dir) return;
    this.dialogKind = kind;
    if (['storage', 'setup'].includes(kind)) {
      this.libraryPath = this.library.storage.library_dir;
      this.modelPath = this.library.storage.model_dir;
      this.folderChoice = null;
    }
    this.cdr.detectChanges();
    this.dialog?.nativeElement.showModal();
  }
  async closeDialog() {
    if (this.dialogKind === 'setup') {
      this.beginWorkflow('setup-close');
      try {
        await this.api('/api/setup/acknowledge', {});
        this.library.storage.setup_seen = true;
      } catch (error) {
        this.fail(error, 'setup-close');
        return;
      }
    }
    this.updateToken = '';
    this.micSession++;
    this.dialogKind = '';
    this.folderChoice = null;
    this.stopCapture();
    this.discardTake();
    this.dialog?.nativeElement.close();
    this.cdr.markForCheck();
  }
  async upload(file: File) {
    const form = new FormData();
    form.append('file', file);
    const response = await fetch('/api/uploads', {
      method: 'POST',
      headers: { 'X-TrogloDAW-Request': '1' },
      body: form,
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || 'Audio upload failed');
    return data;
  }
  async addFiles(event: Event) {
    const input = event.target as HTMLInputElement;
    const files = Array.from(input.files || []);
    input.value = '';
    if (!files.length) return;
    this.audioImports++;
    this.beginWorkflow('audio-input');
    try {
      for (const file of files) await this.acceptFile(file, 'upload');
    } catch (error) {
      this.fail(error, 'audio-input');
    } finally {
      this.audioImports--;
      this.cdr.markForCheck();
    }
  }
  async acceptFile(file: File, type: string, replace = -1) {
    this.beginWorkflow('audio-input');
    this.audioImports++;
    try {
      await this.reportActivity();
      const uploaded = await this.upload(file);
      const job = await this.submit('accept_audio', {
        uploads: [uploaded.id],
        source_type: type,
      });
      const accepted = job.result.accepted[0];
      const clip: Clip = {
        key: crypto.randomUUID(),
        id: accepted.item.id,
        label: accepted.item.name,
        source_type: type,
        audio: accepted.audio,
        settings: {},
      };
      if (replace >= 0) this.draft.clips[replace] = clip;
      else this.draft.clips.push(clip);
      this.saveDraft();
      this.cdr.markForCheck();
    } finally {
      this.audioImports--;
      void this.reportActivity().catch(() => {});
    }
  }
  async replaceFile(event: Event, index: number) {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    input.value = '';
    if (!file) return;
    this.beginWorkflow('audio-input');
    try {
      await this.acceptFile(file, 'upload', index);
    } catch (error) {
      this.fail(error, 'audio-input');
    }
  }
  async hydrateClips() {
    for (const clip of this.draft.clips) {
      try {
        clip.audio = (await this.api('/api/items/' + clip.id)).audio;
      } catch {
        // Saved inputs carry independent preview assets even if the catalog source was deleted.
        if (!clip.saved_file) clip.audio = undefined;
      }
    }
    this.cdr.markForCheck();
  }
  async addAudio(item: Item) {
    this.beginWorkflow('audio-input');
    try {
      const preview = await this.api('/api/items/' + item.id);
      let clip = this.draft.clips.find((value) => value.id === item.id);
      if (!clip) {
        clip = {
          key: crypto.randomUUID(),
          id: item.id,
          label: item.name,
          source_type: ['generated', 'mix'].includes(item.type)
            ? 'prior-song'
            : item.source_type || 'upload',
          audio: preview.audio,
          settings: {},
        };
        this.draft.clips.push(clip);
      }
      this.closeDialog();
      this.changeTab(0);
      if (clip.source_type === 'prior-song' && !clip.preset) {
        this.presetClip = clip;
        this.openDialog('preset');
      }
      this.saveDraft();
    } catch (error) {
      this.fail(error, 'audio-input');
    }
  }
  choosePreset(choice: 'apply' | 'keep') {
    if (this.presetClip) {
      this.presetClip.preset = choice;
      if (choice === 'apply')
        this.presetClip.settings = {
          sample_seconds: 1,
          samples: 8,
          pitch: 2,
          stretch: 1.1,
          gain: -12,
        };
    }
    this.closeDialog();
    this.saveDraft();
  }
  removeClip(index: number) {
    this.draft.clips.splice(index, 1);
    this.saveDraft();
  }
  async generate() {
    if (this.generationCountError) {
      document.getElementById('generation-count')?.focus();
      return;
    }
    try {
      await this.submit('song_generate', this.draft);
    } catch (error) {
      this.fail(error);
    }
  }
  async generateLyrics() {
    try {
      await this.submit('lyrics_generate', {
        prompt:
          this.draft.lyric_idea || [this.draft.title, this.draft.styles].filter(Boolean).join('. '),
        language: this.draft.lyric_language,
      });
    } catch (error) {
      this.fail(error);
    }
  }
  get automaticDuration() {
    const value = this.draft.options['duration'];
    return value == null || value === '' || String(value).toLowerCase() === 'auto';
  }
  async selectSong(item: Item) {
    const selection = ++this.librarySelection;
    this.beginWorkflow('library');
    this.selectedSong = item.id;
    this.songName = item.name;
    this.songFolder = item.folder || '';
    this.libraryAudio = null;
    this.libraryAssets = [];
    this.libraryPreviewError = '';
    this.libraryLoading = true;
    try {
      const preview = await this.api('/api/items/' + item.id);
      if (selection !== this.librarySelection) return;
      this.libraryAudio = preview.audio;
      this.libraryAssets = preview.assets || [];
    } catch (error) {
      if (selection === this.librarySelection) {
        this.libraryPreviewError =
          'Could not load this song preview. Retry, or refresh the library.';
        this.fail(error, 'library');
      }
    } finally {
      if (selection === this.librarySelection) this.libraryLoading = false;
      this.cdr.markForCheck();
    }
  }
  async organize() {
    try {
      await this.submit('organize', {
        id: this.selectedSong,
        name: this.songName,
        folder: this.songFolder,
      });
    } catch (error) {
      this.fail(error);
    }
  }
  async createFolder() {
    try {
      await this.submit('folder', { name: this.newFolder });
      this.newFolder = '';
    } catch (error) {
      this.fail(error);
    }
  }
  async deleteSong() {
    if (!this.selectedSong || !confirm('Delete this song from the library?')) return;
    const id = this.selectedSong;
    try {
      await this.submit('delete', { id });
      if (this.selectedSong === id) {
        this.librarySelection++;
        this.selectedSong = '';
        this.libraryAudio = null;
        this.libraryAssets = [];
        this.libraryLoading = false;
        this.libraryPreviewError = '';
      }
    } catch (error) {
      this.fail(error);
    }
  }
  async referenceSong(item: Item) {
    this.beginWorkflow('library');
    try {
      this.reference = await this.api('/api/ingredients/' + item.id);
      this.referenceFields = {};
      this.closeDialog();
      this.openDialog('reference');
    } catch (error) {
      this.fail(error, 'library');
    }
  }
  applyReference() {
    if (this.reference)
      for (const key of this.referenceKeys)
        if (this.referenceFields[key]) {
          const value = structuredClone(this.reference.available[key]);
          if (key === 'clips')
            this.draft.clips = value.map((clip: any) => ({
              ...clip,
              key: crypto.randomUUID(),
              source_type: clip.source_type || 'upload',
              settings: clip.settings || {},
            }));
          else if (key === 'options') this.draft.options = { ...defaults().options, ...value };
          else (this.draft as any)[key] = value;
        }
    this.closeDialog();
    this.changeTab(0);
    this.saveDraft();
    void this.hydrateClips();
  }
  referenceLabel(key: string) {
    return (
      (
        {
          clips: 'Original input audio',
          styles: 'Styles',
          lyrics: 'Lyrics',
          title: 'Title',
          options: 'Generation controls',
          audio_mode: 'Input audio generation mode',
          audio_adherence: 'Audio adherence',
          arrangement: 'Sample transformations and placements',
        } as Record<string, string>
      )[key] || key
    );
  }
  async editFx(item: Item) {
    this.fxSongId = item.id;
    this.fx = null;
    this.fxPreview = null;
    this.fxPreviewSettings = '';
    this.fxGroup = '';
    this.changeTab(2);
    try {
      await this.submit('vocal_prepare', { song_id: item.id });
    } catch (error) {
      this.fail(error);
    }
  }
  referenceValue(key: string) {
    const value = this.reference?.available[key];
    if (typeof value === 'string') return value;
    if (key === 'clips') return value?.map((clip: Clip) => clip.label).join(', ');
    if (key === 'arrangement')
      return `${value?.samples?.length || 0} transformed samples · ${value?.placements?.length || 0} placements`;
    return JSON.stringify(value, null, 2);
  }
  fxValue(field: Field): Value {
    return this.currentGroup?.settings[field.key] ?? field.initial;
  }
  setFx(key: string, value: Value) {
    if (this.currentGroup) this.currentGroup.settings[key] = value;
  }
  addVoiceGroup(index: number) {
    if (!this.fx) return;
    let next = 1;
    while (this.fx.groups.some((group: any) => group.id === 'g' + next)) next++;
    const id = 'g' + next;
    this.fx.groups.push({
      id,
      name: 'Corrected voice group ' + next,
      settings: { normalize: false },
      uncertain: true,
    });
    this.fx.segments[index].group = id;
  }
  async applyGrouping() {
    try {
      await this.submit('vocal_prepare', {
        song_id: this.fxSongId,
        segments: this.fx.segments,
      });
    } catch (error) {
      this.fail(error);
    }
  }
  fxSave() {
    if (this.fx?.song.recipe?.op === 'vocal-fx-song') this.openDialog('fx-save');
    else void this.renderFx(true, 'new');
  }
  async renderFx(save: boolean, mode: string) {
    this.closeDialog();
    const settings = this.fxSettings;
    try {
      const rendered = await this.submit('vocal_render', {
        song_id: this.fxSongId,
        group_settings: Object.fromEntries(
          this.fx.groups.map((group: any) => [group.id, group.settings]),
        ),
        segments: this.fx.segments,
        name: this.fxName,
        save,
        mode,
      });
      if (this.fxPreview?.url === rendered.result?.audio?.url) this.fxPreviewSettings = settings;
      this.cdr.markForCheck();
    } catch (error) {
      this.fail(error);
    }
  }
  async chooseFolder(kind: 'library' | 'model') {
    if (this.choosingFolder || this.storageBusy) return;
    this.choosingFolder = true;
    this.beginWorkflow('storage');
    try {
      const selection = await this.api('/api/storage/pick', { kind });
      if (selection.path && ['storage', 'setup'].includes(this.dialogKind))
        await this.prepareFolder(kind, selection.path);
    } catch (error) {
      this.fail(error, 'storage');
    } finally {
      this.choosingFolder = false;
      this.cdr.markForCheck();
    }
  }
  async prepareFolder(kind: 'library' | 'model', path: string) {
    this.beginWorkflow('storage');
    try {
      const storage = (await this.api('/api/library')).storage;
      const from = kind === 'library' ? storage.library_dir : storage.model_dir;
      const same = storage.native_folder_picker
        ? path.replaceAll('\\', '/').replace(/\/+$/, '').toLowerCase() ===
          from.replaceAll('\\', '/').replace(/\/+$/, '').toLowerCase()
        : path === from;
      if (same) return;
      if (kind === 'library' ? storage.library_has_data : storage.model_has_data) {
        this.folderChoice = { kind, path, from };
        this.cdr.detectChanges();
        document.getElementById('folder-choice-heading')?.focus();
      } else {
        await this.applyFolder(kind, path, 'open');
      }
    } catch (error) {
      this.fail(error, 'storage');
    }
  }
  async acceptFolder(mode: 'move' | 'open') {
    const choice = this.folderChoice;
    if (!choice || this.storageBusy) return;
    await this.applyFolder(choice.kind, choice.path, mode);
  }
  cancelFolderChoice() {
    this.folderChoice = null;
    this.libraryPath = this.library.storage.library_dir;
    this.modelPath = this.library.storage.model_dir;
  }
  async applyFolder(kind: 'library' | 'model', path: string, mode: string) {
    try {
      const result = await this.submit('storage', { kind, mode, path });
      if (result.status === 'complete') {
        this.libraryPath = this.library.storage.library_dir;
        this.modelPath = this.library.storage.model_dir;
        this.folderChoice = null;
      }
    } catch (error) {
      this.fail(error);
    } finally {
      this.cdr.markForCheck();
    }
  }
  async installModel(planner = false) {
    if (
      this.folderChoice ||
      this.choosingFolder ||
      this.modelPath !== this.library.storage.model_dir
    )
      return;
    try {
      const choice = this.modelChoice;
      await this.submit('model_install', { model: choice, planner });
    } catch (error) {
      this.fail(error);
    }
  }
  get selectedModel() {
    return this.library.models.choices.find((choice: any) => choice.id === this.modelChoice);
  }
  async beginRecording(index = -1) {
    if (this.requestingMic || this.recording) return;
    const session = ++this.micSession;
    this.requestingMic = true;
    this.beginWorkflow('audio-input');
    this.retakeIndex = index;
    this.discardTake();
    if (this.dialogKind !== 'microphone') this.openDialog('microphone');
    try {
      if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === 'undefined')
        throw new Error(
          'Recording needs a supported browser on localhost or a secure connection. Upload an audio file instead.',
        );
      await this.reportActivity();
      const capture = await navigator.mediaDevices.getUserMedia({
        audio: true,
      });
      if (this.dialogKind !== 'microphone' || session !== this.micSession) {
        capture.getTracks().forEach((track) => track.stop());
        return;
      }
      this.capture = capture;
      const mimeType = ['audio/webm;codecs=opus', 'audio/ogg;codecs=opus', 'audio/mp4'].find(
        (type) => MediaRecorder.isTypeSupported(type),
      );
      this.recorder = new MediaRecorder(this.capture, mimeType ? { mimeType } : {});
      const recorder = this.recorder;
      const chunks: Blob[] = [];
      this.recorder.ondataavailable = (event) => {
        if (event.data.size) chunks.push(event.data);
      };
      this.recorder.onerror = () => {
        this.stopCapture();
        this.fail(new Error('Recording failed. Check the microphone and retry.'), 'audio-input');
      };
      this.recorder.onstop = () => {
        capture.getTracks().forEach((track) => track.stop());
        if (this.recorder !== recorder || session !== this.micSession) return;
        this.recording = false;
        this.capture = undefined;
        const blob = new Blob(chunks, {
          type: recorder.mimeType || mimeType || 'audio/webm',
        });
        if (this.dialogKind !== 'microphone') return;
        if (!blob.size) {
          this.fail(new Error('The take was empty. Record again or upload audio.'), 'audio-input');
          return;
        }
        const extension = blob.type.includes('mp4')
          ? 'm4a'
          : blob.type.includes('ogg')
            ? 'ogg'
            : 'webm';
        this.take = new File([blob], 'Microphone take.' + extension, {
          type: blob.type,
        });
        this.takeUrl = URL.createObjectURL(blob);
        this.cdr.markForCheck();
      };
      this.recorder.start();
      this.recording = true;
      this.cdr.markForCheck();
    } catch (error) {
      this.stopCapture();
      const name = error instanceof DOMException ? error.name : '';
      this.fail(
        name === 'NotAllowedError'
          ? new Error(
              'Microphone access was denied. Allow it in this browser or upload a recording.',
            )
          : name === 'NotFoundError'
            ? new Error('No microphone is available. Connect one or upload a recording.')
            : error,
        'audio-input',
      );
    } finally {
      this.requestingMic = false;
      void this.reportActivity().catch(() => {});
      this.cdr.markForCheck();
    }
  }
  stopCapture() {
    if (this.recorder?.state === 'recording') this.recorder.stop();
    this.capture?.getTracks().forEach((track) => track.stop());
    this.capture = undefined;
    this.recording = false;
    void this.reportActivity().catch(() => {});
  }
  discardTake() {
    if (this.takeUrl) URL.revokeObjectURL(this.takeUrl);
    this.take = undefined;
    this.takeUrl = '';
  }
  async keepTake() {
    if (!this.take) return;
    try {
      await this.acceptFile(this.take, 'microphone', this.retakeIndex);
      this.closeDialog();
    } catch (error) {
      this.fail(error, 'audio-input');
    }
  }
  @HostListener('window:beforeunload') cleanup() {
    this.micSession++;
    this.stopCapture();
    this.discardTake();
    if (this.updateTimer) clearTimeout(this.updateTimer);
  }
  async reportActivity() {
    const active = this.recording || this.requestingMic || this.audioImports > 0;
    if (active && !this.captureTimer) {
      this.captureTimer = setInterval(() => void this.reportActivity().catch(() => {}), 5000);
    } else if (!active && this.captureTimer) {
      clearInterval(this.captureTimer);
      this.captureTimer = undefined;
    }
    await fetch('/api/updates/capture', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-TrogloDAW-Request': '1',
      },
      body: JSON.stringify({ client_id: this.captureClient, active }),
      keepalive: !active,
    }).then(async (response) => {
      if (!response.ok && active)
        throw new Error(
          (await response.json()).detail || 'The app is not accepting recordings or uploads.',
        );
    });
  }
  get updateBusy() {
    return ['checking', 'downloading', 'handoff', 'waiting', 'installing', 'restarting'].includes(
      this.update.phase,
    );
  }
  get canInstallUpdate() {
    return (
      this.update.phase === 'ready' &&
      this.update.install_allowed !== false &&
      !this.busy &&
      !this.recording &&
      !this.requestingMic &&
      !this.choosingFolder
    );
  }
  async refreshUpdates() {
    if (this.updateTimer) clearTimeout(this.updateTimer);
    try {
      const next = await this.api('/api/updates');
      if (this.updateHandoff && !next.helper && next.version === this.update.available_version) {
        window.location.reload();
        return;
      }
      this.update = next;
    } catch {
      // A brief listener change is expected during the explicit installer handoff.
      if (!this.updateHandoff && !this.stopped)
        this.update = {
          ...this.update,
          status_error:
            'Could not read update status. Reopen the app or use the browser release link if this continues.',
        };
    } finally {
      this.cdr.markForCheck();
      if (!this.stopped && this.update.phase !== 'source')
        this.updateTimer = setTimeout(
          () => void this.refreshUpdates(),
          this.updateBusy || this.update.phase === 'ready' ? 700 : 10000,
        );
    }
  }
  async updateAction(action: string, values: any = {}) {
    this.beginWorkflow('updates');
    if (action === 'check') {
      this.update = {
        ...this.update,
        phase: 'checking',
        message: 'Checking for the latest release…',
        status_error: undefined,
        available_version: null,
      };
      this.cdr.markForCheck();
    }
    try {
      this.update = await this.api('/api/updates/' + action, values);
      void this.refreshUpdates();
    } catch (error) {
      if (action === 'check')
        this.update = {
          ...this.update,
          phase: 'failed',
          message:
            'Could not start the update check. Retry or open the latest release in your browser.',
        };
      this.fail(error, 'updates');
    } finally {
      this.cdr.markForCheck();
    }
  }
  async saveUpdateAccess() {
    try {
      await this.updateAction('access', { token: this.updateToken });
    } finally {
      this.updateToken = '';
    }
  }
  openUpdates() {
    this.openDialog('storage');
    document.getElementById('app-updates')?.setAttribute('open', '');
  }
  async installUpdate() {
    if (!this.canInstallUpdate) return;
    this.beginWorkflow('updates');
    try {
      this.update = await this.api('/api/updates/apply', {});
      this.cleanup();
      document.querySelectorAll('audio').forEach((audio) => audio.pause());
      this.closeDialog();
      this.updateHandoff = true;
      this.cdr.markForCheck();
      requestAnimationFrame(() => document.getElementById('update-heading')?.focus());
      void this.refreshUpdates();
    } catch (error) {
      this.fail(error, 'updates');
    }
  }
  toggleTheme() {
    this.appearance = this.theme === 'light' ? 'dark' : 'light';
    try {
      localStorage.setItem('troglodaw-theme', this.appearance);
    } catch {}
    this.applyAppearance();
  }
  useSystemTheme() {
    this.appearance = 'system';
    try {
      localStorage.removeItem('troglodaw-theme');
    } catch {}
    this.applyAppearance();
  }
  private applyAppearance() {
    this.theme =
      this.appearance === 'dark' || (this.appearance === 'system' && this.systemAppearance.matches)
        ? 'dark'
        : 'light';
    document.documentElement.classList.toggle('dark', this.theme === 'dark');
    document.documentElement.dataset.theme = this.theme;
    window.dispatchEvent(new Event('troglodaw-theme-change'));
    this.cdr.markForCheck();
  }
  async quit() {
    if (this.quitting || this.stopped) return;
    this.quitting = true;
    this.beginWorkflow('quit');
    try {
      await this.api('/api/shutdown', {});
      this.cleanup();
      document.querySelectorAll('audio').forEach((audio) => audio.pause());
      this.closeDialog();
      this.stopped = true;
      this.cdr.markForCheck();
      requestAnimationFrame(() => document.getElementById('quit-heading')?.focus());
    } catch (error) {
      this.fail(error, 'quit');
    } finally {
      this.quitting = false;
      this.cdr.markForCheck();
    }
  }
}
