import copy
import shutil

import numpy as np

from test_source_routing import mixed_audio, instrumental_evidence


def test_mixed_collection_saves_effective_roles_without_changing_draft_and_replays(
    core, songs, tmp_path, monkeypatch
):
    service, _ = songs
    # Qualify the invented continuous harmony fixture as instrumental. Unknown
    # continuous mixes cannot authorize arbitrary cuts through possible words.
    monkeypatch.setattr(
        service,
        "source_phrases",
        lambda path, audio, *args: instrumental_evidence(audio, core.SR)
        if len(audio) > 8 * core.SR
        else {"status": "fallback"},
    )
    prior = core._new_entry(
        "generated", "synthetic completed mix", mixed_audio(core.SR, 12), "fixture"
    )
    voice = core._new_entry("voice", "quiet recording", core.synth_voice(3) * 0.04, "fixture")
    originals = [core.load_item(item["id"]).copy() for item in (prior, voice)]
    draft = {
        "clips": [{"id": prior["id"]}, {"id": voice["id"], "settings": {"pitch": -2}}],
        "styles": "industrial, no guitars",
        "lyrics": "Keep these exact words.",
        "options": {"duration": 20},
        "count": 1,
        "audio_mode": "postmix",
    }
    before = copy.deepcopy(draft)
    result = service.generate(draft, lambda *_a, **_k: None, lambda: False)
    assert result["outcomes"][0]["status"] == "complete", result
    song = result["outcomes"][0]["song"]
    recipe = song["recipe"]
    assert draft == before
    assert [source["routing"]["role"] for source in recipe["sources"]] == [
        "mix-accent",
        "recording-phrase",
    ]
    assert {sample["source_id"] for sample in recipe["samples"]} == {prior["id"], voice["id"]}
    assert all(
        source["routing"]["collection"] == "one-prior+one-recording" for source in recipe["sources"]
    )
    assert recipe["parameters"]["lyrics"] == draft["lyrics"]
    for item, original in zip((prior, voice), originals):
        np.testing.assert_array_equal(core.load_item(item["id"]), original)
    expected = core.load_item(song["id"])
    moved = tmp_path / "moved-library"
    shutil.copytree(core.LIB, moved)
    monkeypatch.setattr(core, "LIB", moved)
    monkeypatch.setattr(core, "CATALOG", moved / "catalog.json")
    monkeypatch.setattr(core, "INBOX", moved / "inbox")
    replay = service.rerender(song["id"])
    np.testing.assert_allclose(core.load_item(replay["id"]), expected, atol=1 / 32768)
