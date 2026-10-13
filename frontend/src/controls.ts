import {
  AfterViewInit,
  Component,
  ChangeDetectorRef,
  inject,
  ElementRef,
  EventEmitter,
  Input,
  OnChanges,
  Output,
  ViewChild,
  HostListener,
  OnDestroy,
  SimpleChanges,
} from '@angular/core';
import { FormsModule } from '@angular/forms';

export type Value = string | number | boolean;
export interface Option {
  label: string;
  value: string;
}
export interface Field {
  key: string;
  label: string;
  kind: 'text' | 'number' | 'slider' | 'select' | 'check' | 'radio';
  initial: Value;
  min?: number;
  max?: number;
  step?: number;
  choices?: string[];
}
export interface Media {
  url: string;
  name: string;
}

@Component({
  selector: 'troglodaw-icon',
  template: `<svg
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="1.5"
    aria-hidden="true"
  >
    @switch (name) {
      @case ('note') {
        <path d="M9 18V5l12-2v12" />
        <ellipse cx="6" cy="18" rx="3" ry="2.5" />
        <ellipse cx="18" cy="15" rx="3" ry="2.5" />
      }
      @case ('upload') {
        <path d="M12 16V3m-5 5 5-5 5 5M4 14v7h16v-7" />
      }
      @case ('volume') {
        <path d="m10 5-5 4H2v6h3l5 4V5m4 3c3 2 3 6 0 8m3-11c5 4 5 10 0 14" />
      }
      @default {
        <path d="M6 2h8l5 5v15H6V2m8 0v6h5" />
      }
    }
  </svg>`,
})
export class IconComponent {
  @Input() name = 'file';
}

@Component({
  selector: 'troglodaw-field',
  imports: [FormsModule],
  template: `
    @if (field.kind === 'check') {
      <label class="check-label"
        ><input
          type="checkbox"
          [ngModel]="mixed ? false : value"
          [indeterminate]="mixed"
          (ngModelChange)="valueChange.emit($event)"
        />{{ field.label }}
        @if (mixed) {
          <span class="mixed-value">Mixed</span>
        }
      </label>
    } @else {
      <div class="field-header">
        <label [for]="field.key"
          >{{ field.label }}
          @if (mixed) {
            <span class="mixed-value">Mixed</span>
          }
        </label>
        @if (field.kind === 'slider') {
          <span class="slider-number"
            ><input
              type="number"
              [attr.aria-label]="field.label + ' value'"
              [ngModel]="mixed ? null : value"
              [placeholder]="mixed ? 'Mixed' : ''"
              (ngModelChange)="valueChange.emit($event)"
              [step]="field.step"
              [min]="field.min ?? null"
              [max]="field.max ?? null"
            /><button
              type="button"
              [attr.aria-label]="'Reset ' + field.label"
              (click)="valueChange.emit(field.initial)"
            >
              ↺
            </button></span
          >
        }
      </div>
      @switch (field.kind) {
        @case ('slider') {
          <div class="range-row">
            <span>{{ field.min }}</span
            ><input
              [id]="field.key"
              type="range"
              [min]="field.min"
              [max]="field.max"
              [step]="field.step"
              [ngModel]="mixed ? field.initial : value"
              (ngModelChange)="valueChange.emit(+$event)"
              [style.--fill]="fill() + '%'"
            /><span>{{ field.max }}</span>
          </div>
        }
        @case ('select') {
          <div class="select-wrap">
            <select [id]="field.key" [ngModel]="value" (ngModelChange)="valueChange.emit($event)">
              @if (!hasEmptyOption()) {
                <option value=""></option>
              }
              @for (option of options; track option.value) {
                <option [value]="option.value">{{ option.label }}</option>
              }</select
            ><span aria-hidden="true">⌄</span>
          </div>
        }
        @case ('radio') {
          <div class="radio-row">
            @for (choice of field.choices; track choice) {
              <label
                ><input
                  type="radio"
                  [name]="field.key"
                  [value]="choice"
                  [ngModel]="value"
                  (ngModelChange)="valueChange.emit($event)"
                />{{ choice }}</label
              >
            }
          </div>
        }
        @default {
          <input
            [id]="field.key"
            [type]="field.kind === 'number' ? 'number' : 'text'"
            [ngModel]="value"
            (ngModelChange)="valueChange.emit($event)"
            [step]="field.step || 1"
          />
        }
      }
    }
  `,
})
export class FieldComponent {
  @Input({ required: true }) field!: Field;
  @Input() value: Value = '';
  @Input() mixed = false;
  @Input() options: Option[] = [];
  @Output() valueChange = new EventEmitter<Value>();
  hasEmptyOption() {
    return this.options.some((option) => option.value === '');
  }
  fill() {
    if (this.mixed) return 50;
    return (
      ((Number(this.value) - (this.field.min || 0)) /
        ((this.field.max || 1) - (this.field.min || 0))) *
      100
    );
  }
}

@Component({
  selector: 'troglodaw-upload',
  imports: [IconComponent],
  template: `<div class="upload-panel" (dragover)="$event.preventDefault()" (drop)="drop($event)">
    <label class="corner-label" [for]="id"><troglodaw-icon />{{ label }}</label>
    <input
      [id]="id"
      type="file"
      [multiple]="multiple"
      [attr.accept]="accept || null"
      (change)="choose($event)"
      hidden
    />
    @if (files.length) {
      <div class="file-list">
        @for (file of files; track $index) {
          <div>
            <span>{{ file.name }}</span
            ><button
              type="button"
              [attr.aria-label]="'Remove ' + file.name"
              (click)="remove($index)"
            >
              ×
            </button>
          </div>
        }
      </div>
    } @else {
      <label class="drop-target" [for]="id"
        ><span class="upload-icon"><troglodaw-icon name="upload" /></span><span>Drop File Here</span
        ><span class="muted">- or -</span><span>Click to Upload</span></label
      >
    }
  </div>`,
})
export class UploadComponent {
  @Input() label = '';
  @Input() id = 'upload';
  @Input() multiple = false;
  @Input() accept = '';
  @Input() files: File[] = [];
  @Output() filesChange = new EventEmitter<File[]>();
  choose(event: Event) {
    const el = event.target as HTMLInputElement;
    this.emit(el.files);
    el.value = '';
  }
  drop(event: DragEvent) {
    event.preventDefault();
    this.emit(event.dataTransfer?.files || null);
  }
  emit(files: FileList | null) {
    this.filesChange.emit(files ? Array.from(files).slice(0, this.multiple ? undefined : 1) : []);
  }
  remove(index: number) {
    this.filesChange.emit(this.files.filter((_, i) => i !== index));
  }
}

@Component({
  selector: 'troglodaw-download',
  imports: [IconComponent],
  template: `<div class="download-panel">
    <span class="corner-label"><troglodaw-icon />{{ label }}</span>
    @if (media) {
      <a [href]="media.url + '?download=true'" download>{{ media.name }} <span>↓</span></a>
    } @else {
      <span class="empty-file" aria-hidden="true"><troglodaw-icon /></span>
    }
  </div>`,
})
export class DownloadComponent {
  @Input() label = '';
  @Input() media: Media | null = null;
}

@Component({
  selector: 'troglodaw-audio',
  imports: [FormsModule, IconComponent],
  template: `<div class="audio-panel" [class.has-audio]="media">
    <span class="corner-label" [title]="label"
      ><troglodaw-icon name="note" /><span>{{ label }}</span></span
    >
    @if (media) {
      <a
        class="audio-download"
        [href]="media.url + '?download=true'"
        download
        [attr.aria-label]="'Download ' + label"
        title="Download audio"
        >↓</a
      >
    }
    <audio
      #player
      [src]="media?.url || ''"
      (timeupdate)="syncTime(player)"
      (seeking)="syncTime(player)"
      (seeked)="syncTime(player)"
      (play)="playing = true"
      (pause)="playing = false"
      (ended)="playing = false; syncTime(player)"
      (volumechange)="muted = player.muted"
      (ratechange)="rate = player.playbackRate"
      (error)="playbackFailed()"
      (loadedmetadata)="duration = player.duration; syncTime(player)"
    ></audio>
    @if (media) {
      <div class="audio-waveform">
        <canvas
          #wave
          width="1000"
          height="64"
          role="img"
          [attr.aria-label]="label + ' waveform'"
          (click)="seek($event, player)"
        ></canvas>
        <span
          class="audio-playhead"
          [style.--position]="playheadPosition + '%'"
          aria-hidden="true"
        ></span>
      </div>
      <div class="audio-timeline">
        <span>{{ clock(time) }}</span
        ><span>{{ clock(duration, true) }}</span>
      </div>
      <div class="audio-controls">
        <button
          type="button"
          (click)="player.muted = !player.muted; muted = player.muted"
          [attr.aria-label]="(muted ? 'Unmute ' : 'Mute ') + label"
          [attr.aria-pressed]="muted"
          [title]="muted ? 'Unmute audio' : 'Mute audio'"
          [class.muted-audio]="muted"
        >
          @if (muted) {
            <span>×</span>
          } @else {
            <troglodaw-icon name="volume" />
          }
        </button>
        <select
          aria-label="Playback speed"
          [ngModel]="rate"
          (ngModelChange)="rate = $event; player.playbackRate = +$event"
        >
          @for (speed of [0.5, 0.75, 1, 1.25, 1.5, 2]; track speed) {
            <option [value]="speed">{{ speed }}x</option>
          }
        </select>
        <div class="transport">
          <button type="button" (click)="skip(player, -15)" [attr.aria-label]="'Rewind ' + label">
            ◀◀</button
          ><button
            type="button"
            (click)="play(player)"
            [attr.aria-label]="(playing ? 'Pause ' : 'Play ') + label"
          >
            {{ playing ? 'Ⅱ' : '▶' }}</button
          ><button type="button" (click)="skip(player, 15)" [attr.aria-label]="'Forward ' + label">
            ▶▶
          </button>
        </div>
      </div>
      @if (feedback) {
        <p class="audio-feedback" role="status">{{ feedback }}</p>
      }
    } @else {
      <span class="empty-note" aria-hidden="true"><troglodaw-icon name="note" /></span>
    }
  </div>`,
})
export class AudioComponent implements OnChanges, AfterViewInit, OnDestroy {
  private cdr = inject(ChangeDetectorRef);
  @Input() label = '';
  @Input() media: Media | null = null;
  @ViewChild('player') player?: ElementRef<HTMLAudioElement>;
  wave?: ElementRef<HTMLCanvasElement>;
  @ViewChild('wave') set waveformElement(element: ElementRef<HTMLCanvasElement> | undefined) {
    this.resize?.disconnect();
    this.wave = element;
    if (element) {
      this.resize = new ResizeObserver(() => this.draw());
      this.resize.observe(element.nativeElement);
      this.draw();
    }
  }
  playing = false;
  time = 0;
  duration = 0;
  rate = 1;
  muted = false;
  feedback = '';
  samples?: Float32Array;
  private resize?: ResizeObserver;
  get playheadPosition() {
    return Number.isFinite(this.duration) && this.duration > 0 && Number.isFinite(this.time)
      ? Math.max(0, Math.min(100, (this.time / this.duration) * 100))
      : 0;
  }
  syncTime(player: HTMLAudioElement) {
    this.time = Number.isFinite(player.currentTime) ? player.currentTime : 0;
  }
  async ngOnChanges(changes: SimpleChanges) {
    if (!changes['media'] || changes['media'].previousValue?.url === this.media?.url) return;
    this.playing = false;
    this.time = 0;
    this.duration = 0;
    this.rate = 1;
    this.muted = false;
    this.feedback = '';
    this.samples = undefined;
    if (this.player) {
      this.player.nativeElement.pause();
      this.player.nativeElement.muted = false;
      this.player.nativeElement.playbackRate = 1;
    }
    this.draw();
    if (!this.media) return;
    const url = this.media.url;
    try {
      const buffer = await (await fetch(url)).arrayBuffer();
      const context = new AudioContext();
      try {
        const audio = await context.decodeAudioData(buffer);
        if (this.media?.url === url) {
          this.samples = audio.getChannelData(0);
          this.duration = audio.duration;
          this.draw();
        }
      } finally {
        await context.close();
      }
    } catch {
      /* The audio element reports unsupported playback without blocking other controls. */
    }
  }
  ngAfterViewInit() {
    this.draw();
  }
  ngOnDestroy() {
    this.resize?.disconnect();
    this.wave = undefined;
  }
  draw() {
    const canvas = this.wave?.nativeElement;
    if (!canvas) return;
    if (canvas.getBoundingClientRect().width <= 0) return;
    const context = canvas.getContext('2d')!;
    context.clearRect(0, 0, canvas.width, canvas.height);
    if (!this.samples) return;
    context.fillStyle =
      getComputedStyle(document.documentElement).getPropertyValue('--waveform').trim() || '#9ca3af';
    const bars = Math.max(1, Math.floor(canvas.getBoundingClientRect().width / 5));
    const width = canvas.width / bars;
    for (let bar = 0; bar < bars; bar++) {
      let peak = 0;
      const step = Math.max(1, Math.floor(this.samples.length / bars));
      for (let i = bar * step; i < Math.min((bar + 1) * step, this.samples.length); i++)
        peak = Math.max(peak, Math.abs(this.samples[i]));
      const height = Math.max(2, peak * 48);
      context.fillRect(bar * width, (64 - height) / 2, width * 0.4, height);
    }
    this.cdr.markForCheck();
  }
  @HostListener('window:troglodaw-theme-change') themeChanged() {
    this.draw();
  }
  async play(player: HTMLAudioElement) {
    const url = this.media?.url;
    this.feedback = '';
    if (this.playing) {
      player.pause();
      this.playing = false;
    } else {
      try {
        await player.play();
        if (this.media?.url === url) this.playing = !player.paused;
      } catch {
        if (this.media?.url === url) this.playbackFailed();
      }
    }
  }
  seek(event: MouseEvent, player: HTMLAudioElement) {
    const box = (event.target as HTMLElement).getBoundingClientRect();
    if (Number.isFinite(player.duration))
      player.currentTime =
        Math.max(0, Math.min(1, (event.clientX - box.left) / box.width)) * player.duration;
    this.syncTime(player);
  }
  skip(player: HTMLAudioElement, seconds: number) {
    if (Number.isFinite(player.duration))
      player.currentTime = Math.min(player.duration, Math.max(0, player.currentTime + seconds));
    this.syncTime(player);
  }
  playbackFailed() {
    if (!this.media) return;
    this.playing = false;
    this.feedback = 'Could not play this audio. Try Play again or download the file.';
    this.cdr.markForCheck();
  }
  clock(value: number, round = false) {
    value = round ? Math.round(value) : value;
    return Number.isFinite(value)
      ? `${Math.floor(value / 60)}:${Math.floor(value % 60)
          .toString()
          .padStart(2, '0')}`
      : '0:00';
  }
}
