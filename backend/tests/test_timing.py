from timing import History, Tracking


class Clock:
    now = 0.0

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


PROFILE = {
    "operation": "song_generate",
    "model": "base",
    "backend": "cuda",
    "duration": 60,
    "outputs": 1,
}


def test_unknown_work_is_not_a_timer_percentage_and_live_units_are_provisional(tmp_path):
    clock = Clock()
    tracking = Tracking(History(tmp_path / "timing.json"), PROFILE, clock)
    clock.advance(7)
    tracking.start()
    tracking.update("Loading", 0.9, stage="loading")
    clock.advance(5)
    state = tracking.snapshot()
    assert state["stage_progress"] is None and state["stage_remaining"] is None
    assert state["estimate_state"] == "estimating"
    assert state["queue_wait_seconds"] == 7 and state["elapsed_seconds"] == 5
    tracking.update("Generating", stage="generating", units_complete=0, units_total=10)
    for unit in [1, 2]:
        clock.advance(2)
        tracking.update("Generating", stage="generating", units_complete=unit, units_total=10)
    state = tracking.snapshot()
    assert state["stage_progress"] == 0.2
    assert state["stage_remaining"]["basis"] == "live_units"
    assert state["estimate_state"] == "provisional" and state["request_remaining"] is None
    clock.advance(10)
    tracking.update("Generating", stage="generating", units_complete=3, units_total=10)
    assert tracking.snapshot()["estimate_state"] == "taking_longer"


def test_qualified_history_does_not_pool_cpu_gpu_or_cached_fresh(tmp_path):
    path = tmp_path / "timing.json"
    history = History(path)
    for elapsed in [90, 100]:
        history.observe("request", PROFILE, elapsed)
    assert history.estimate("request", PROFILE) is None
    history.observe("request", PROFILE, 110)
    reopened = History(path)
    assert reopened.estimate("request", PROFILE)["samples"] == 3
    assert reopened.estimate("request", {**PROFILE, "backend": "cpu"}) is None
    assert reopened.estimate("request", {**PROFILE, "cache_hit": True}) is None
    assert reopened.estimate("request", {**PROFILE, "duration": 120}) is None
    clock = Clock()
    tracking = Tracking(reopened, PROFILE, clock)
    tracking.start()
    clock.advance(30)
    assert tracking.snapshot()["request_remaining"]["high"] > 60
    clock.advance(150)
    assert tracking.snapshot()["request_remaining"] is None
    assert tracking.snapshot()["estimate_state"] == "taking_longer"


def test_item_history_estimates_remaining_sequential_outputs(tmp_path):
    history = History(tmp_path / "timing.json")
    for elapsed in [40, 42, 44]:
        history.observe("item", {k: v for k, v in PROFILE.items() if k != "outputs"}, elapsed)
    clock = Clock()
    tracking = Tracking(history, {**PROFILE, "outputs": 3}, clock)
    tracking.start()
    tracking.update("Loading", stage="loading", item=1, items_total=3)
    clock.advance(10)
    state = tracking.snapshot()
    assert state["item_remaining"] and state["request_remaining"]
    assert state["request_remaining"]["low"] > state["item_remaining"]["high"]


def test_running_never_finishes_and_terminal_elapsed_and_ranges_freeze(tmp_path):
    clock = Clock()
    history = History(tmp_path / "timing.json")
    tracking = Tracking(history, PROFILE, clock)
    tracking.start()
    tracking.update("Rendering", stage="rendering", units_complete=1, units_total=1)
    assert tracking.snapshot()["stage_progress"] < 1
    clock.advance(8)
    tracking.finish("canceled")
    clock.advance(50)
    state = tracking.snapshot()
    assert state["elapsed_seconds"] == 8
    assert state["stage_remaining"] is state["item_remaining"] is state["request_remaining"] is None
    assert history.estimate("request", PROFILE) is None
    assert state["estimate_state"] == "finished"


def test_failed_or_partial_outputs_do_not_train_successful_request_totals(tmp_path):
    history = History(tmp_path / "timing.json")
    clock = Clock()
    for status in ["failed", "canceled", "complete"]:
        tracking = Tracking(history, PROFILE, clock)
        tracking.start()
        clock.advance(30)
        tracking.update("Output failed", stage="failed_item", outcomes=[{"status": "failed"}])
        tracking.finish(status)
    assert history.estimate("request", PROFILE) is None


def test_corrupt_history_degrades_to_unknown_without_affecting_work(tmp_path):
    path = tmp_path / "timing.json"
    path.write_text("interrupted write")
    history = History(path)
    assert history.estimate("request", PROFILE) is None
    for seconds in [20, 21, 22]:
        history.observe("request", PROFILE, seconds)
    assert History(path).estimate("request", PROFILE)


def test_per_asset_stage_context_does_not_pollute_request_history(tmp_path):
    history = History(tmp_path / "timing.json")
    for _ in range(3):
        clock = Clock()
        tracking = Tracking(history, PROFILE, clock)
        tracking.start()
        for asset, seconds in [("first", 10), ("second", 20)]:
            tracking.update(
                "Verifying",
                stage="verifying",
                timing_stage_profile={"asset": asset},
                units_complete=0,
                units_total=100,
            )
            clock.advance(seconds)
            tracking.update("Verified", stage="verifying", units_complete=100, units_total=100)
        tracking.finish("complete")
        assert "asset" not in tracking.profile
    assert history.estimate("request", PROFILE)["samples"] == 3
    stage = {k: v for k, v in PROFILE.items() if k != "outputs"}
    assert (
        history.estimate("stage", {**stage, "asset": "first", "stage_device": ""}, "verifying")[
            "high"
        ]
        < history.estimate("stage", {**stage, "asset": "second", "stage_device": ""}, "verifying")[
            "low"
        ]
    )


def test_device_change_resets_live_stage_rate(tmp_path):
    clock = Clock()
    tracking = Tracking(History(tmp_path / "timing.json"), PROFILE, clock)
    tracking.start()
    tracking.update(
        "Separating", stage="separating", stage_device="cuda", units_complete=0, units_total=10
    )
    for count in [1, 2]:
        clock.advance(1)
        tracking.update("Separating", stage="separating", units_complete=count, units_total=10)
    assert tracking.snapshot()["stage_remaining"]
    tracking.update(
        "CPU fallback",
        stage="separating",
        stage_device="cpu",
        timing_profile={"backend": "cpu"},
        units_complete=0,
        units_total=10,
    )
    assert tracking.snapshot()["stage_remaining"] is None
    assert tracking.stage_profile["stage_device"] == "cpu"


def test_no_new_work_events_make_a_stalled_live_estimate_unknown(tmp_path):
    clock = Clock()
    tracking = Tracking(History(tmp_path / "timing.json"), PROFILE, clock)
    tracking.start()
    tracking.update("Generating", stage="generating", units_complete=0, units_total=10)
    for count in [1, 2, 3]:
        clock.advance(1)
        tracking.update("Generating", stage="generating", units_complete=count, units_total=10)
    assert tracking.snapshot()["stage_remaining"]
    clock.advance(8)
    assert tracking.snapshot()["stage_remaining"] is None
    assert tracking.snapshot()["estimate_state"] == "taking_longer"
    assert tracking.snapshot()["stage_progress"] == 0.3


def test_download_range_uses_live_transfer_speed_for_all_known_model_files(tmp_path):
    clock = Clock()
    tracking = Tracking(History(tmp_path / "timing.json"), {"operation": "model_install"}, clock)
    tracking.start()
    for done in [0, 10, 20]:
        tracking.update(
            "Downloading",
            stage="downloading",
            units_complete=done,
            units_total=100,
            download_bytes_complete=50 + done,
            download_bytes_total=1000,
        )
        clock.advance(1)
    state = tracking.snapshot()
    assert state["download_remaining"]["basis"] == "live_units"
    assert state["download_remaining"]["low"] > state["stage_remaining"]["high"]
    tracking.update("Verifying", stage="verifying", units_complete=0, units_total=100)
    assert tracking.snapshot()["download_remaining"] is None


def test_previous_gpu_history_waits_for_current_device_confirmation(tmp_path):
    history = History(tmp_path / "timing.json")
    for seconds in [10, 11, 12]:
        history.observe("request", PROFILE, seconds)
    tracking = Tracking(history, PROFILE, Clock(), confirm_hardware=True)
    tracking.start()
    assert tracking.snapshot()["request_remaining"] is None
    tracking.update("CPU fallback", stage="loading", timing_profile={"backend": "cpu"})
    assert tracking.snapshot()["request_remaining"] is None


def test_duplicate_work_messages_do_not_qualify_or_refresh_live_speed(tmp_path):
    clock = Clock()
    tracking = Tracking(History(tmp_path / "timing.json"), PROFILE, clock)
    tracking.start()
    for _ in range(4):
        tracking.update("Starting", stage="generating", units_complete=0, units_total=10)
        clock.advance(1)
    tracking.update("Step", stage="generating", units_complete=1, units_total=10)
    assert tracking.snapshot()["stage_remaining"] is None
    clock.advance(1)
    tracking.update("Step", stage="generating", units_complete=2, units_total=10)
    assert tracking.snapshot()["stage_remaining"]
    clock.advance(10)
    tracking.update("Still working", stage="generating", units_complete=2, units_total=10)
    assert tracking.snapshot()["stage_remaining"] is None
