import copy
import json

import pytest

from prompt_enrichment import (
    CODEC,
    PROMPT_VERSION,
    accepted,
    asset_identity,
    checked_verdict,
    parse_additions,
    profile_for,
    provenance,
    requested,
)


def manifest():
    music = {
        "assets": [{"path": "weights", "bytes": 3, "sha256": "fixture"}],
        "enrichment_profile": "p",
    }
    return {
        "runtime_revision": "r",
        "models": {"music": music},
        "enrichment_profiles": {
            "p": {
                "id": "p",
                "qualified": True,
                "music_runtime_revision": "r",
                "music_asset_identity": asset_identity(music),
                "prompt_version": PROMPT_VERSION,
                "codec": CODEC,
                "writer": "fixture",
                "writer_revision": "revision",
            }
        },
    }


@pytest.mark.parametrize(
    "change", ["unknown-model", "unqualified", "runtime", "weights", "prompt", "codec"]
)
def test_changed_or_unqualified_identity_has_no_profile(change):
    value = manifest()
    if change == "unknown-model":
        assert profile_for(value, "unknown") is None
        return
    if change == "unqualified":
        value["enrichment_profiles"]["p"]["qualified"] = False
    if change == "runtime":
        value["runtime_revision"] = "changed"
    if change == "weights":
        value["models"]["music"]["assets"][0]["sha256"] = "changed"
    if change == "prompt":
        value["enrichment_profiles"]["p"]["prompt_version"] = "untested"
    if change == "codec":
        value["enrichment_profiles"]["p"]["codec"] = "untested"
    assert profile_for(value, "music") is None


def test_matching_identity_does_not_mutate_manifest():
    value = manifest()
    original = copy.deepcopy(value)
    assert profile_for(value, "music")["id"] == "p"
    assert value == original


@pytest.mark.parametrize(
    "response,reason",
    [
        ("not json", "malformed-proposal"),
        ("[]", "malformed-proposal"),
        ('{"additions":null}', "malformed-proposal"),
        ('{"additions":false}', "malformed-proposal"),
        ("{}", "no-additions"),
        ('{"additions":"  "}', "no-additions"),
        (json.dumps({"additions": "x" * 301}), "oversized-proposal"),
    ],
)
def test_bad_or_empty_proposals_fall_back(response, reason):
    assert parse_additions(response) == ("", reason)


def test_checked_unicode_addition_keeps_literal_original_caption():
    caption = "政治演説、楽器なし\nKeep these fucking words exactly. "
    additions, reason = parse_additions(json.dumps({"additions": "  明確な発音  "}))
    assert reason is None and additions == "明確な発音"
    assert accepted("ACCEPT") and not accepted("ACCEPT but add a piano") and not accepted("REJECT")
    info = provenance(caption, profile=profile_for(manifest(), "music"), additions=additions)
    assert info["original_caption"] == caption and info["effective_caption"].startswith(caption)
    fallback = provenance(caption, reason="rejected-proposal")
    assert fallback["effective_caption"] == caption and not fallback["applied"]


def test_default_and_explicit_off_are_strict_boolean_choices():
    assert requested({}) and not requested({"prompt_enrichment": False})
    for value in [None, 0, 1, "off", "true", []]:
        with pytest.raises(ValueError, match="on or off"):
            requested({"prompt_enrichment": value})


@pytest.mark.parametrize(
    "response",
    [
        "ACCEPT",
        "not json",
        "[]",
        '{"verdict":"ACCEPT"}',
        '{"verdict":"ACCEPT","conflict":null}',
        '{"verdict":"ACCEPT","conflict":"adds excluded instruments"}',
        '{"verdict":"REJECT","conflict":""}',
    ],
)
def test_only_valid_conflict_free_check_results_can_pass(response):
    assert checked_verdict(response) == "REJECT"
    assert checked_verdict('{"verdict":"ACCEPT","conflict":""}') == "ACCEPT"
