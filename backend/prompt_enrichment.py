"""Versioned additive prompt contracts; lyrics and source audio are never rewritten."""

from __future__ import annotations

import hashlib
import json


PROMPT_VERSION = "production-details-v1"
CODEC = "bnb-nf4-double-v1"
WRITER_PROMPT = (
    'Return exactly {"additions":"..."} with a string at most 120 characters. Help an '
    "underspecified music prompt express its genre clearly. If the request already provides "
    "a specific instrumental/performance plan, or asks for speech, vocal-only, solo-instrument "
    'or sparse/quiet material, return {"additions":""}; extra instructions can hurt those '
    "requests. For a broad genre/era/mood request lacking instrumental detail, describe a few "
    "defining compatible instrumental sounds, articulation or groove. Use concise descriptive "
    "sound phrases, not use/add/increase commands. Never repeat or change the requested genre, "
    "era or mood; do not invent sound effects, ambient noise, visuals, subject matter, lyrics, "
    "vocals for instrumentals, prohibited instruments or another genre. Keep every explicit "
    "exclusion. Do not use geographic stereotypes. Original text and lyrics remain unchanged. "
    "Empty additions are appropriate when there is no confident improvement. The input object "
    "contains the original request and delivery context. Instrumental means no vocal additions. "
    "An authoritative audio source must keep its words, structure and identity."
)
CHECK_PROMPT = 'Evaluate proposed additional audio directions against an original request that remains verbatim. First identify any specific conflict, then decide. Return exactly JSON with conflict and verdict: {"conflict":"the concrete conflict or empty string", "verdict":"ACCEPT or REJECT"}. For physical playing techniques, consider how the actual instrument makes and sustains sound, its controls and whether the proposed action can cause that sound. For other proposals check genre/era/mood, explicit instrument limits (solo, a named ensemble, no instruments), no-vocal/no-music/spoken delivery, sparse/quiet intent, extraneous sound effects, visual directions, invented topics/lyrics. A broad genre request allows genre-appropriate musical instruments even when not named; these are not sound effects. No lyrics are rewritten. Accept only when there is no conflict; when uncertain reject. Profanity and political or other subject matter are not grounds for rejection: this is not moderation.'


def asset_identity(model):
    identity = sorted(
        (asset["path"], asset["bytes"], asset["sha256"]) for asset in model.get("assets", [])
    )
    return hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()


def profile_for(manifest, model):
    music = manifest.get("models", {}).get(model, {})
    profile = manifest.get("enrichment_profiles", {}).get(music.get("enrichment_profile"), {})
    if (
        profile.get("qualified") is not True
        or profile.get("music_runtime_revision") != manifest.get("runtime_revision")
        or profile.get("music_asset_identity") != asset_identity(music)
        or profile.get("prompt_version") != PROMPT_VERSION
        or profile.get("codec") != CODEC
    ):
        return None
    return profile


def requested(draft):
    value = draft.get("prompt_enrichment", True)
    if not isinstance(value, bool):
        raise ValueError("Enrich prompt must be on or off")
    return value


def parse_additions(response, maximum=300):
    try:
        value = json.loads(response)
    except (ValueError, TypeError):
        return "", "malformed-proposal"
    if not isinstance(value, dict) or not isinstance(value.get("additions", ""), str):
        return "", "malformed-proposal"
    text = value.get("additions", "").strip()
    if not text:
        return "", "no-additions"
    if len(text) > maximum:
        return "", "oversized-proposal"
    return text, None


def accepted(verdict):
    return isinstance(verdict, str) and verdict.strip() == "ACCEPT"


def checked_verdict(response):
    try:
        value = json.loads(response)
    except (ValueError, TypeError):
        return "REJECT"
    if isinstance(value, dict) and value.get("verdict") == "ACCEPT" and value.get("conflict") == "":
        return "ACCEPT"
    return "REJECT"


def provenance(caption, enabled=True, profile=None, reason=None, additions="", **details):
    return {
        "requested": enabled,
        "applied": bool(additions),
        "profile": profile.get("id") if profile else None,
        "writer": profile.get("writer") if profile else None,
        "writer_revision": profile.get("writer_revision") if profile else None,
        "codec": profile.get("codec") if profile else None,
        "prompt_version": profile.get("prompt_version") if profile else None,
        "original_caption": caption,
        "additions": additions,
        "effective_caption": caption + ("; " + additions if additions else ""),
        "fallback_reason": reason,
        **details,
    }
