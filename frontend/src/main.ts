import { ChangeDetectorRef, Component, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { bootstrapApplication } from '@angular/platform-browser';
import { NgTemplateOutlet } from '@angular/common';
import {
  AudioComponent,
  DownloadComponent,
  Field,
  FieldComponent,
  Media,
  Option,
  UploadComponent,
  Value,
} from './controls';

interface Item {
  id: string;
  type: string;
  name: string;
  duration: number;
  tags: string[];
  created: string;
  source: string;
  path: string;
}
interface Library {
  items: Item[];
  styles: string[];
  library: string;
  inbox: string;
}
interface Result {
  message: string;
  audio: Media | null;
  download: Media | null;
  production?: any;
  song?: any;
}
type Layout = string[][][];
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
const fields: Field[] = [
  field('apVoice', 'Voice from library', 'select', ''),
  field('apStyle', 'Style', 'select', 'auto'),
  field('apMood', 'Mood', 'select', 'auto', undefined, undefined, undefined, [
    'auto',
    'chill',
    'sad',
    'dreamy',
    'classic',
    'groovy',
    'dark',
    'hype',
    'happy',
  ]),
  field('apBpm', 'BPM (0 = detect)', 'number', 0, undefined, undefined, 0.1),
  field('apKey', 'Key (blank = detect), e.g. A minor', 'text', ''),
  field('apTune', 'Pitch correction', 'radio', 'auto', undefined, undefined, undefined, [
    'auto',
    'on',
    'off',
  ]),
  field('apSeed', 'Seed (-1 = random; reuse a seed to reproduce)', 'number', -1),
  field('upType', 'Import as', 'radio', 'voice', undefined, undefined, undefined, [
    'voice',
    'music',
  ]),
  field('upTags', 'Tags (comma separated)', 'text', ''),
  field('libPick', 'Select item', 'select', ''),
  field('libTags', 'Set tags', 'text', ''),
  field('libName', 'Rename', 'text', ''),
  field('fxVoice', 'Voice', 'select', ''),
  field('fxTrim', 'Trim silence', 'check', false),
  field('fxPitch', 'Pitch (semitones)', 'slider', 0, -12, 12, 0.5),
  field('fxStretch', 'Time stretch (tempo factor, >1 faster)', 'slider', 1, 0.5, 2, 0.05),
  field('fxGain', 'Gain (dB)', 'slider', 0, -24, 24, 0.5),
  field('fxLow', 'Low cut / high-pass Hz (0=off)', 'slider', 0, 0, 1000, 10),
  field('fxHigh', 'High cut / low-pass Hz (0=off)', 'slider', 0, 0, 20000, 100),
  field('fxComp', 'Compression', 'check', false),
  field('fxCthr', 'Comp threshold dB', 'slider', -20, -60, 0, 1),
  field('fxCrat', 'Comp ratio', 'slider', 4, 1, 20, 0.5),
  field('fxChorus', 'Chorus mix', 'slider', 0, 0, 1, 0.05),
  field('fxRobot', 'Robot mix', 'slider', 0, 0, 1, 0.05),
  field('fxRhz', 'Robot pitch Hz', 'slider', 110, 40, 400, 5),
  field('fxDelay', 'Echo mix', 'slider', 0, 0, 1, 0.05),
  field('fxDtime', 'Echo time s', 'slider', 0.3, 0.05, 1.5, 0.05),
  field('fxDfb', 'Echo feedback', 'slider', 0.35, 0, 0.9, 0.05),
  field('fxRev', 'Reverb wet', 'slider', 0, 0, 1, 0.05),
  field('fxRoom', 'Room size', 'slider', 0.6, 0, 1, 0.05),
  field('fxNorm', 'Normalize', 'check', true),
  field('fxName', 'Name for saved voice (optional)', 'text', ''),
  field('gBpm', 'BPM', 'slider', 90, 60, 180, 1),
  field('gStyle', 'Drum style', 'select', 'boombap'),
  field('gKey', 'Key (e.g. A minor, C major, F#m, D dorian)', 'text', 'A minor'),
  field(
    'gProg',
    'Progression (roman numerals, blank = default; e.g. i-VI-III-VII, I-V-vi-IV)',
    'text',
    '',
  ),
  field('gBars', 'Length (bars)', 'slider', 8, 1, 64, 1),
  field('gSwing', 'Swing', 'slider', 0, 0, 1, 0.05),
  field('gSeed', 'Seed (-1 = random)', 'number', -1),
  field('gDrums', 'Drums', 'check', true),
  field('gBass', 'Bass', 'check', true),
  field('gPad', 'Chord pad', 'check', true),
  field('gName', 'Name (optional)', 'text', ''),
  field('rmPick', 'Load a saved mix recipe to remix (optional)', 'select', ''),
  field('mVoice', 'Voice', 'select', ''),
  field('mMusic', 'Music (imported, generated, or a previous mix)', 'select', ''),
  field('mVv', 'Voice volume dB', 'slider', 0, -30, 12, 0.5),
  field('mMv', 'Music volume dB', 'slider', -4, -30, 12, 0.5),
  field('mOff', 'Voice offset (s)', 'slider', 2, 0, 60, 0.25),
  field('mDuck', 'Duck music under vocals', 'check', true),
  field('mDd', 'Duck amount dB', 'slider', 8, 0, 24, 0.5),
  field('mFi', 'Fade in s', 'slider', 1, 0, 10, 0.25),
  field('mFo', 'Fade out s', 'slider', 2, 0, 10, 0.25),
  field('mLoop', 'Loop music to fit', 'check', true),
  field('mTail', 'Music tail after voice (s)', 'slider', 2, 0, 20, 0.5),
  field(
    'mFx',
    'Render-time voice FX JSON (optional), e.g. {"pitch": -2, "reverb": 0.3}',
    'text',
    '',
  ),
  field('mName', 'Mix name (optional)', 'text', ''),
];

@Component({
  selector: 'mm-app',
  imports: [
    NgTemplateOutlet,
    FormsModule,
    FieldComponent,
    AudioComponent,
    DownloadComponent,
    UploadComponent,
  ],
  templateUrl: './app.html',
})
export class AppComponent {
  private cdr = inject(ChangeDetectorRef);
  fields = Object.fromEntries(fields.map((f) => [f.key, f]));
  values: Record<string, Value> = Object.fromEntries(fields.map((f) => [f.key, f.initial]));
  library: Library = { items: [], styles: [], library: '', inbox: '' };
  tabs = ['🎤 AI Producer', 'Voice FX', 'Generator', 'Mixer / Remix'];
  tab = 0;
  overrides = false;
  files: File[] = [];
  producerFiles: File[] = [];
  original: Media | null = null;
  playback: Media | null = null;
  catalog = '';
  outputs: Record<string, Result> = {};
  busy: Record<string, boolean> = {};
  progress: Record<string, { message: string; fraction: number }> = {};
  libraryStatus = '';
  error = '';
  theme = 'light';
  settings = false;
  tableFull = false;
  JSON = JSON;
  layouts: Record<string, Layout> = {
    producer: [[['apStyle'], ['apMood'], ['apBpm'], ['apKey'], ['apTune'], ['apSeed']]],
    fxLeft: [
      [['fxTrim'], ['fxPitch'], ['fxStretch'], ['fxGain']],
      [['fxLow', 'fxHigh']],
      [['fxComp', 'fxCthr', 'fxCrat']],
    ],
    fxRight: [
      [['fxChorus']],
      [['fxRobot', 'fxRhz']],
      [['fxDelay', 'fxDtime', 'fxDfb']],
      [['fxRev', 'fxRoom']],
      [['fxNorm'], ['fxName']],
    ],
    generator: [
      [['gBpm'], ['gStyle'], ['gKey'], ['gProg'], ['gBars'], ['gSwing'], ['gSeed']],
      [['gDrums', 'gBass', 'gPad']],
      [['gName']],
    ],
    mixer: [
      [['rmPick'], ['mVoice'], ['mMusic'], ['mVv'], ['mMv'], ['mOff']],
      [['mDuck', 'mDd']],
      [['mFi', 'mFo']],
      [['mLoop', 'mTail']],
      [['mFx'], ['mName']],
    ],
  };
  constructor() {
    this.refresh();
  }
  async api<T>(path: string, body?: unknown): Promise<T> {
    const response = await fetch(
      '/api/' + path,
      body === undefined
        ? {}
        : {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-MusicMaker-Request': '1' },
            body: JSON.stringify(body),
          },
    );
    const data = await response.json();
    if (!response.ok)
      throw Error(typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail));
    return data;
  }
  async refresh() {
    try {
      this.library = await this.api<Library>('library');
      for (const key of ['apVoice', 'fxVoice', 'mVoice', 'mMusic', 'libPick', 'rmPick']) {
        if (this.values[key] && !this.options(key).some((o) => o.value === this.values[key]))
          this.values[key] = '';
      }
      if (!this.values['libPick']) {
        this.playback = null;
        this.catalog = '';
      }
    } catch (e) {
      this.error = String(e);
    }
    this.cdr.markForCheck();
  }
  options(key: string): Option[] {
    const f = this.fields[key];
    if (f.choices) return f.choices.map((value) => ({ label: value, value }));
    if (['apStyle', 'gStyle'].includes(key))
      return (key === 'apStyle' ? ['auto', ...this.library.styles] : this.library.styles).map(
        (value) => ({ label: value, value }),
      );
    const types =
      key === 'mMusic'
        ? ['music', 'generated', 'mix']
        : key === 'rmPick'
          ? ['mix']
          : key === 'libPick'
            ? ['voice', 'music', 'generated', 'mix']
            : ['voice'];
    return this.library.items
      .filter((i) => types.includes(i.type))
      .map((i) => ({
        value: i.id,
        label: `${i.name}  [${i.type}, ${i.duration.toFixed(1)}s]  ·${i.id}`,
      }));
  }
  async change(key: string, value: Value) {
    this.values[key] = value;
    try {
      if (key === 'libPick' || key === 'fxVoice') {
        if (!value) {
          if (key === 'libPick') {
            this.playback = null;
            this.catalog = '';
          } else this.original = null;
        } else {
          const data = await this.api<{ item: Item; audio: Media }>('items/' + value);
          if (key === 'libPick') {
            this.playback = data.audio;
            this.catalog = JSON.stringify(data.item, null, 2);
          } else this.original = data.audio;
        }
      }
      if (key === 'rmPick' && value) {
        const recipe = await this.api<any>('recipes/' + value);
        this.values['mVoice'] = recipe.voice;
        this.values['mMusic'] = recipe.music;
        this.values['mName'] = recipe.name;
        this.values['mFx'] = recipe.fx;
        const keys = ['mVv', 'mMv', 'mOff', 'mDuck', 'mDd', 'mFi', 'mFo', 'mLoop', 'mTail'];
        const settingKeys = [
          'voice_vol',
          'music_vol',
          'offset',
          'duck',
          'duck_db',
          'fade_in',
          'fade_out',
          'loop',
          'tail',
        ];
        keys.forEach((k, i) => (this.values[k] = recipe.settings[settingKeys[i]]));
      }
    } catch (e) {
      this.error = String(e);
    }
    this.cdr.markForCheck();
  }
  map(keys: string[], names: string[]) {
    return Object.fromEntries(keys.map((key, i) => [names[i], this.values[key]]));
  }
  async upload(files: File[]) {
    const ids: string[] = [];
    for (const file of files) {
      const form = new FormData();
      form.append('file', file);
      const response = await fetch('/api/uploads', {
        method: 'POST',
        headers: { 'X-MusicMaker-Request': '1' },
        body: form,
      });
      const result = await response.json();
      if (!response.ok) throw Error(result.detail);
      ids.push(result.id);
    }
    return ids;
  }
  async run(action: string, extra: Record<string, unknown> = {}) {
    const slot = ['import', 'inbox', 'delete', 'tags'].includes(action) ? 'library' : action;
    if (this.busy[slot]) return;
    this.busy[slot] = true;
    this.error = '';
    this.progress[slot] = { message: 'Processing...', fraction: 0 };
    this.cdr.markForCheck();
    try {
      let values: Record<string, unknown> = {};
      switch (action) {
        case 'import':
          values = {
            uploads: await this.upload(this.files),
            type: this.values['upType'],
            tags: this.values['upTags'],
          };
          break;
        case 'inbox':
          values = { type: this.values['upType'] };
          break;
        case 'delete':
          values = { id: this.values['libPick'] };
          break;
        case 'tags':
          values = {
            id: this.values['libPick'],
            name: this.values['libName'],
            tags: this.values['libTags'],
          };
          break;
        case 'fx':
          values = {
            voice: this.values['fxVoice'],
            name: this.values['fxName'],
            settings: this.map(
              [
                'fxTrim',
                'fxPitch',
                'fxStretch',
                'fxGain',
                'fxLow',
                'fxHigh',
                'fxComp',
                'fxCthr',
                'fxCrat',
                'fxChorus',
                'fxRobot',
                'fxRhz',
                'fxDelay',
                'fxDtime',
                'fxDfb',
                'fxRev',
                'fxRoom',
                'fxNorm',
              ],
              [
                'trim',
                'pitch',
                'stretch',
                'gain',
                'low_cut',
                'high_cut',
                'compress',
                'comp_threshold',
                'comp_ratio',
                'chorus',
                'robot',
                'robot_hz',
                'delay',
                'delay_time',
                'delay_feedback',
                'reverb',
                'room_size',
                'normalize',
              ],
            ),
          };
          break;
        case 'generate':
          values = {
            name: this.values['gName'],
            settings: this.map(
              [
                'gBpm',
                'gStyle',
                'gKey',
                'gProg',
                'gBars',
                'gSwing',
                'gSeed',
                'gDrums',
                'gBass',
                'gPad',
              ],
              [
                'bpm',
                'style',
                'key',
                'progression',
                'bars',
                'swing',
                'seed',
                'drums',
                'bass',
                'pad',
              ],
            ),
          };
          break;
        case 'mix':
          values = {
            voice: this.values['mVoice'],
            music: this.values['mMusic'],
            name: this.values['mName'],
            fx: this.values['mFx'],
            settings: this.map(
              ['mVv', 'mMv', 'mOff', 'mDuck', 'mDd', 'mFi', 'mFo', 'mLoop', 'mTail'],
              [
                'voice_vol',
                'music_vol',
                'offset',
                'duck',
                'duck_db',
                'fade_in',
                'fade_out',
                'loop',
                'tail',
              ],
            ),
          };
          break;
        case 'produce':
          values = {
            ...this.map(
              ['apVoice', 'apStyle', 'apMood', 'apBpm', 'apKey', 'apTune', 'apSeed'],
              ['voice', 'style', 'mood', 'bpm', 'key', 'tune', 'seed'],
            ),
            upload: (await this.upload(this.producerFiles))[0],
          };
          break;
      }
      const job = await this.api<{ id: string }>('jobs', {
        action,
        values: { ...values, ...extra },
      });
      while (true) {
        const state = await this.api<{
          status: string;
          message: string;
          progress: number;
          result: Result;
        }>('jobs/' + job.id);
        this.progress[slot] = { message: state.message, fraction: state.progress };
        this.cdr.markForCheck();
        if (['complete', 'failed'].includes(state.status)) {
          if (slot === 'library') this.libraryStatus = state.result.message;
          else this.outputs[slot] = state.result;
          await this.refresh();
          break;
        }
        await new Promise((resolve) => setTimeout(resolve, 150));
      }
    } catch (e) {
      const message = String(e);
      if (slot === 'library') this.libraryStatus = message;
      else this.outputs[slot] = { message, audio: null, download: null };
    } finally {
      this.busy[slot] = false;
      this.cdr.markForCheck();
    }
  }
  async copyTable() {
    const headers = ['id', 'type', 'name', 'dur(s)', 'tags', 'created', 'source'];
    const rows = this.library.items.map((i) => [
      i.id,
      i.type,
      i.name,
      i.duration.toFixed(2),
      i.tags.join(','),
      i.created,
      i.source,
    ]);
    try {
      await navigator.clipboard.writeText(
        [headers, ...rows].map((row) => row.join('\t')).join('\n'),
      );
    } catch {
      this.error = 'Could not copy the catalog table.';
      this.cdr.markForCheck();
    }
  }
  async quit() {
    try {
      const result = await this.api<{ message: string }>('shutdown', {});
      this.libraryStatus = result.message;
    } catch (e) {
      this.libraryStatus = String(e);
    }
    this.cdr.markForCheck();
  }
  setTheme() {
    document.documentElement.classList.toggle(
      'dark',
      this.theme === 'dark' ||
        (this.theme === 'system' && matchMedia('(prefers-color-scheme: dark)').matches),
    );
  }
  productionRows() {
    const pr = this.outputs['produce']?.production;
    if (!pr) return [];
    const an = pr.analysis,
      ch = pr.choices;
    return [
      ['Style', `${ch.style} (${ch.style_source})`],
      ['Tempo', `${ch.bpm} BPM (${ch.tempo_source})`],
      ['Key', `${ch.key} (${ch.key_source})`],
      ['Chords', ch.progression],
      [
        'Vocal',
        `${an.sung ? 'sung' : 'spoken / rap'}, ${an.n_phrases} phrases, ${an.active_seconds} s active, ${an.loudness_lufs} LUFS raw`,
      ],
      [
        'Pitch correction',
        pr.chain.pitch_correction
          ? `on (${pr.chain.corrections_semitones.length} notes nudged)`
          : 'off',
      ],
      ['Arrangement', pr.sections.map((s: any) => `${s.name} (${s.bars})`).join(' → ')],
      ['Seed', pr.params.seed],
    ];
  }
}
bootstrapApplication(AppComponent).catch(console.error);
