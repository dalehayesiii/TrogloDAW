"""Bounded local measurements and honest live stage/item/job timing."""

from __future__ import annotations

import hashlib
import json
import math
import statistics
import time
from pathlib import Path

from storage import atomic_json

TERMINAL = {"complete", "failed", "canceled"}


def key(scope, profile, stage=None):
    return hashlib.sha256(json.dumps([scope, profile, stage], sort_keys=True).encode()).hexdigest()


class History:
    def __init__(self, path: Path):
        self.path = path
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            self.rows = value["rows"] if value.get("version") == 1 else {}
            if not isinstance(self.rows, dict):
                self.rows = {}
            self.rows = {
                identifier: [
                    v
                    for v in samples[-12:]
                    if isinstance(v, (int, float)) and math.isfinite(v) and v > 0
                ]
                for identifier, samples in list(self.rows.items())[-256:]
                if isinstance(samples, list)
            }
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            self.rows = {}

    def observe(self, scope, profile, seconds, stage=None):
        if not math.isfinite(seconds) or seconds <= 0:
            return
        identifier = key(scope, profile, stage)
        samples = self.rows.pop(identifier, [])
        self.rows[identifier] = [*samples[-11:], round(seconds, 4)]
        while len(self.rows) > 256:
            del self.rows[next(iter(self.rows))]
        try:
            atomic_json(self.path, {"version": 1, "rows": self.rows})
        except OSError:
            # A read-only/full settings directory must not fail audio processing.
            pass

    def estimate(self, scope, profile, stage=None):
        samples = self.rows.get(key(scope, profile, stage), [])
        if len(samples) < 3:
            return None
        ordered = sorted(samples)
        middle = statistics.median(ordered)
        # Small-sample observed envelope, not a statistical coverage guarantee.
        low = max(0.1, min(ordered) * 0.85)
        high = max(max(ordered) * 1.15, middle * 1.25)
        return {"low": low, "high": high, "samples": len(samples), "basis": "local_history"}


class Tracking:
    def __init__(self, history, profile, clock=time.monotonic, *, confirm_hardware=False):
        self.history, self.profile, self.clock = history, dict(profile), clock
        self.hardware_confirmed = not confirm_hardware
        self.created = clock()
        self.started = self.ended = self.stage_started = None
        self.stage = "queued"
        self.stage_profile = dict(profile)
        self.item_started = None
        self.item = self.items_total = 1
        self.finished_items = 0
        self.units_complete = self.units_total = None
        self.unit_samples = []
        self.rate = None
        self.status = "queued"
        self.stage_completed = False
        self.changed_until = 0
        self.details = {}

    def start(self):
        self.started = self.item_started = self.clock()
        self.status = "running"
        self.stage = "initializing"
        self.stage_started = self.started

    def item_profile(self):
        return {k: v for k, v in self.profile.items() if k != "outputs"}

    def _observe_stage(self, successful=True):
        if (
            self.stage_started is not None
            and successful
            and self.stage not in {"initializing", "failed_item", "output_complete", "context"}
        ):
            self.history.observe(
                "stage", self.stage_profile, self.clock() - self.stage_started, self.stage
            )

    def update(self, message, fraction=0, **details):
        now = self.clock()
        profile = details.pop("timing_profile", {})
        stage_context = details.pop("timing_stage_profile", None)
        # Profiles contain performance context only, never audio/lyrics/paths.
        if profile:
            self.profile.update(profile)
            if "backend" in profile:
                self.hardware_confirmed = True
        item = int(details.get("item", self.item))
        self.items_total = int(details.get("items_total", self.items_total))
        self.profile["outputs"] = self.items_total
        if item != self.item:
            self.item, self.item_started = item, now
        stage = details.get("stage") or self.stage
        stage_profile = {
            **self.item_profile(),
            **(stage_context or {}),
            "stage_device": details.get(
                "stage_device",
                self.stage_profile.get("stage_device", "") if stage == self.stage else "",
            ),
        }
        if stage_context is None and stage == self.stage:
            stage_profile.update(
                {
                    k: v
                    for k, v in self.stage_profile.items()
                    if k not in self.item_profile() and k != "stage_device"
                }
            )
        if stage != self.stage or stage_profile != self.stage_profile:
            self._observe_stage(
                (stage != self.stage or self.stage_completed) and stage != "failed_item"
            )
            self.stage, self.stage_started, self.stage_profile = stage, now, stage_profile
            self.units_complete = self.units_total = None
            self.unit_samples, self.rate = [], None
            self.stage_completed = False
        done, total = details.get("units_complete"), details.get("units_total")
        if done is not None and total is not None and total > 0:
            self.units_complete, self.units_total = max(0, done), total
            advanced = not self.unit_samples or done != self.unit_samples[-1][1]
            if advanced:
                self.unit_samples.append((now, done))
                self.unit_samples = self.unit_samples[-8:]
            if advanced and len(self.unit_samples) > 1:
                old_time, old_done = self.unit_samples[-2]
                if now > old_time and done > old_done:
                    rate = (now - old_time) / (done - old_done)
                    if self.rate is not None and rate > self.rate * 1.5:
                        self.changed_until = now + 8
                    self.rate = rate if self.rate is None else self.rate * 0.6 + rate * 0.4
            self.stage_completed = done >= total
        if stage == "output_complete":
            outcomes = details.get("outcomes", [])
            if (
                outcomes
                and outcomes[-1].get("status") == "complete"
                and self.item_started is not None
            ):
                self.history.observe("item", self.item_profile(), now - self.item_started)
            self.finished_items = len(outcomes)
        self.details.update(details)

    def finish(self, status):
        self.status, self.ended = status, self.clock()
        if status == "complete":
            self._observe_stage()
            # Do not train request totals on partial per-output failures.
            outcomes = self.details.get("outcomes", [])
            if self.started is not None and (
                not outcomes or all(o.get("status") == "complete" for o in outcomes)
            ):
                self.history.observe("request", self.profile, self.ended - self.started)
        elif self.stage_completed:
            self._observe_stage()

    def _remaining(self, prediction, elapsed):
        if prediction is None or elapsed > prediction["high"]:
            return None
        return {
            **prediction,
            "low": max(1, prediction["low"] - elapsed),
            "high": max(1, prediction["high"] - elapsed),
        }

    def snapshot(self):
        now = self.ended if self.ended is not None else self.clock()
        terminal = self.status in TERMINAL
        elapsed = max(0, now - self.started) if self.started is not None else 0
        queued = max(0, (self.started if self.started is not None else now) - self.created)
        stage_elapsed = max(0, now - self.stage_started) if self.stage_started is not None else 0
        stage_history = self.history.estimate("stage", self.stage_profile, self.stage)
        request_history = (
            self.history.estimate("request", self.profile) if self.hardware_confirmed else None
        )
        item_history = (
            self.history.estimate("item", self.item_profile()) if self.hardware_confirmed else None
        )
        stage_eta = self._remaining(stage_history, stage_elapsed)
        download_eta = None
        stalled = False
        # Completed work units give a provisional rate; never treat a timer as work.
        if self.rate is not None and self.units_total and len(self.unit_samples) >= 3:
            remaining = max(0, self.units_total - self.units_complete) * self.rate
            live = {
                "low": max(1, remaining * 0.75),
                "high": max(1, remaining * 1.35),
                "samples": len(self.unit_samples),
                "basis": "live_units",
            }
            stage_eta = live
            if self.stage == "downloading" and self.details.get("download_bytes_total"):
                bytes_left = max(
                    0,
                    self.details["download_bytes_total"]
                    - self.details.get("download_bytes_complete", 0),
                )
                download_eta = {
                    **live,
                    "low": max(1, bytes_left * self.rate * 0.75),
                    "high": max(1, bytes_left * self.rate * 1.35),
                }
            intervals = [
                b[0] - a[0]
                for a, b in zip(self.unit_samples, self.unit_samples[1:])
                if b[1] > a[1] and b[0] > a[0]
            ]
            if intervals and self.units_complete < self.units_total:
                idle = now - self.unit_samples[-1][0]
                stalled = idle > max(2, statistics.median(intervals) * 2)
                if stalled:
                    stage_eta = None
                    download_eta = None
        item_elapsed = now - self.item_started if self.item_started is not None else 0
        item_eta = self._remaining(item_history, item_elapsed)
        total_eta = self._remaining(request_history, elapsed)
        if total_eta is None and item_eta is not None and item_history is not None:
            remaining_items = max(0, self.items_total - self.item)
            total_eta = {
                **item_eta,
                "low": item_eta["low"] + item_history["low"] * remaining_items,
                "high": item_eta["high"] + item_history["high"] * remaining_items,
            }
        if terminal:
            stage_eta = item_eta = total_eta = None
            download_eta = None
        slower = bool(
            not terminal
            and (
                stage_history
                and stage_elapsed > stage_history["high"]
                or request_history
                and elapsed > request_history["high"]
                or self.changed_until > now
                or stalled
            )
        )
        progress = None
        if self.units_total:
            progress = min(0.99, self.units_complete / self.units_total)
        return {
            "stage": self.stage,
            "elapsed_seconds": round(elapsed, 1),
            "queue_wait_seconds": round(queued, 1),
            "stage_elapsed_seconds": round(stage_elapsed, 1),
            "stage_progress": 1 if self.status == "complete" else progress,
            "units_complete": self.units_complete,
            "units_total": self.units_total,
            "stage_remaining": stage_eta,
            "item_remaining": item_eta,
            "request_remaining": total_eta,
            "download_remaining": download_eta,
            "estimate_state": "finished"
            if terminal
            else "taking_longer"
            if slower
            else "calibrated"
            if total_eta
            else "stage_calibrated"
            if stage_eta and stage_eta["basis"] == "local_history"
            else "provisional"
            if stage_eta
            else "estimating",
        }
