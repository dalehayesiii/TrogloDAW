import { TestBed } from '@angular/core/testing';
import { describe, expect, it } from 'vitest';
import { FieldComponent, UploadComponent } from './controls';

describe('Gradio control contracts', () => {
  it('emits the original slider default when reset', async () => {
    const fixture = TestBed.createComponent(FieldComponent);
    fixture.componentRef.setInput('field', {
      key: 'pitch',
      label: 'Pitch (semitones)',
      kind: 'slider',
      initial: 0,
      min: -12,
      max: 12,
      step: 0.5,
    });
    fixture.componentRef.setInput('value', 4);
    const values: unknown[] = [];
    fixture.componentInstance.valueChange.subscribe((value) => values.push(value));
    await fixture.whenStable();
    fixture.nativeElement.querySelector('button').click();
    expect(values).toEqual([0]);
    expect(fixture.componentInstance.fill()).toBeCloseTo(66.67, 1);
  });
  it('keeps original checkbox defaults and emits changes', async () => {
    const fixture = TestBed.createComponent(FieldComponent);
    fixture.componentRef.setInput('field', {
      key: 'norm',
      label: 'Normalize',
      kind: 'check',
      initial: true,
    });
    fixture.componentRef.setInput('value', true);
    await fixture.whenStable();
    expect(fixture.nativeElement.querySelector('input').checked).toBe(true);
  });
  it('supports single and multiple uploads and removing a selected file', () => {
    const fixture = TestBed.createComponent(UploadComponent);
    const a = new File(['a'], 'a.wav'),
      b = new File(['b'], 'b.wav');
    const files: File[][] = [];
    fixture.componentInstance.filesChange.subscribe((value) => files.push(value));
    const list = { 0: a, 1: b, length: 2, item: (i: number) => [a, b][i] } as unknown as FileList;
    fixture.componentInstance.emit(list);
    expect(files[0]).toEqual([a]);
    fixture.componentInstance.multiple = true;
    fixture.componentInstance.emit(list);
    expect(files[1]).toEqual([a, b]);
    fixture.componentInstance.files = [a, b];
    fixture.componentInstance.remove(0);
    expect(files[2]).toEqual([b]);
  });
});
