"""Clip cards for the media bin.

A card is what the UI shows while analysis is still running. It is filled from
whatever the pipeline has written so far. Failures name the cause and the fix.
Talking and Scenic are the words on the card; the stored role stays a_roll or
b_roll so the existing cut contract does not change.
"""

from __future__ import annotations

from typing import Any

_FIXES = {
    "no audio track": "This clip has no audio track. Add a clip with sound, or exclude it.",
    "unsupported codec": "Unsupported codec: convert to H.264, then retry.",
    "hevc": "Unsupported codec: convert to H.264, then retry.",
}


def clip_card(analysis: dict[str, Any] | None, *, path: str, name: str | None = None) -> dict[str, Any]:
    analysis = analysis or {}
    probe = analysis.get("probe") or {}
    status = analysis.get("status") or "pending"
    error = analysis.get("error")
    flags = _flags(analysis)
    if error and status != "complete":
        status = "error"
    return {
        "path": path,
        "name": name or path.rsplit("/", 1)[-1],
        "status": status,
        "duration_s": probe.get("duration_s"),
        "shot_at": analysis.get("shot_at"),
        "camera": _camera(probe, path),
        "kind": _kind(analysis),
        "flags": flags,
        "error": _friendly(error) if error else None,
        "retry": status == "error",
    }


def order_clips(cards: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(cards, key=lambda card: (card.get("shot_at") or "", card.get("name") or ""))


def group_cards(cards: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: list[dict[str, Any]] = []
    index: dict[tuple[str, str], dict[str, Any]] = {}
    for card in order_clips(cards):
        day = (card.get("shot_at") or "Unknown day")[:10]
        camera = card.get("camera") or "Unknown camera"
        key = (day, camera)
        group = index.get(key)
        if group is None:
            group = {"day": day, "camera": camera, "clips": []}
            index[key] = group
            groups.append(group)
        group["clips"].append(card)
    return groups


def style_sentence(profile: dict[str, Any]) -> str:
    """Plain-language style card. Example: about 9 cuts a minute, most shots 2–5 s."""
    cuts = profile.get("cuts_per_minute") or 0
    length = profile.get("shot_length") or {}
    low = _seconds(length.get("p10"))
    high = _seconds(length.get("p90"))
    talking = round(100 * float(profile.get("speech_share") or 0))
    runtime = profile.get("runtime_s") or 0
    minutes = max(1, round(float(runtime) / 60)) if runtime else 0
    runtime_bit = f", around {minutes} minutes" if minutes else ""
    return f"About {round(cuts)} cuts a minute, most shots {low}–{high} s, {talking}% talking{runtime_bit}."


def _kind(analysis: dict[str, Any]) -> str | None:
    if analysis.get("status") not in {"complete", "running"} and not analysis.get("shots"):
        return None
    shots = analysis.get("shots") or []
    if not shots:
        return None
    talking = sum(1 for shot in shots if shot.get("role_hint") == "a_roll" or (shot.get("speech_share") or 0) >= 0.3)
    return "Talking" if talking >= max(1, len(shots) / 2) else "Scenic"


def _flags(analysis: dict[str, Any]) -> list[str]:
    flags: list[str] = []
    probe = analysis.get("probe") or {}
    if analysis.get("status") == "complete" and probe and not probe.get("has_audio", True):
        flags.append("No audio track")
    for shot in analysis.get("shots") or []:
        quality = shot.get("quality") or {}
        for reason in quality.get("reject_reasons") or []:
            label = _flag_label(reason, shot)
            if label not in flags:
                flags.append(label)
    return flags


def _flag_label(reason: str, shot: dict[str, Any]) -> str:
    start = _clock(shot.get("in_s"))
    end = _clock(shot.get("out_s"))
    span = f" {start}–{end}" if start and end else ""
    names = {
        "shaky": "Shaky",
        "blurry": "Blurry",
        "black": "Too dark",
        "overexposed": "Too bright",
        "no_frames": "No frames",
    }
    return f"{names.get(reason, reason)}{span}"


def _friendly(error: str) -> str:
    lowered = error.lower()
    for needle, message in _FIXES.items():
        if needle in lowered:
            return message
    if "audio" in lowered:
        return "No audio track. Exclude this clip or replace it."
    return error


def _camera(probe: dict[str, Any], path: str) -> str:
    name = path.rsplit("/", 1)[-1].upper()
    if name.startswith("GOPR") or name.startswith("GX"):
        return "GoPro"
    if name.startswith("IMG_") or name.startswith("DJI"):
        return "iPhone" if name.startswith("IMG_") else "DJI"
    make = (probe.get("make") or probe.get("camera") or "").strip()
    return make or "Camera"


def _seconds(value: float | None) -> str:
    if value is None:
        return "?"
    rounded = round(float(value))
    return str(max(1, rounded))


def _clock(seconds: float | None) -> str:
    if seconds is None:
        return ""
    total = int(seconds)
    return f"{total // 60}:{total % 60:02d}"
