from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field

from ave.edl.schema import EDL

MIN_SEGMENT_S = 0.3
TARGET_TOLERANCE = 0.10


class ValidationIssue(BaseModel):
    code: str
    message: str
    segment_id: str | None = None


class ValidationResult(BaseModel):
    ok: bool
    errors: list[ValidationIssue] = Field(default_factory=list)


@dataclass
class Word:
    word: str
    start: float
    end: float


@dataclass
class ClipInfo:
    path: Path
    duration_s: float
    shot_at: datetime | None = None
    words: list[Word] = field(default_factory=list)


class MediaIndex:
    def __init__(self, clips: dict[str, ClipInfo] | None = None):
        self._clips: dict[str, ClipInfo] = {}
        if clips:
            for c in clips.values():
                self.add(c)

    def add(self, clip: ClipInfo) -> None:
        self._clips[str(clip.path.resolve())] = clip
        self._clips[str(clip.path)] = clip
        self._clips[clip.path.name] = clip

    def get(self, source: str, base: Path | None = None) -> ClipInfo | None:
        p = Path(source)
        if base and not p.is_absolute():
            p = (base / p).resolve()
        elif p.exists():
            p = p.resolve()
        for key in (str(p), source, p.name):
            if key in self._clips:
                return self._clips[key]
        return None

    def __len__(self) -> int:
        return len({id(v) for v in self._clips.values()})


def validate_edl(
    edl: EDL,
    index: MediaIndex,
    *,
    base: Path | None = None,
    check_words: bool = True,
    check_order: bool = True,
    check_target: bool = True,
) -> ValidationResult:
    errors: list[ValidationIssue] = []
    used_ranges: list[tuple[str, float, float, str]] = []
    prev_order: tuple[datetime, float] | None = None

    if not edl.segments:
        errors.append(ValidationIssue(code="empty", message="EDL has no segments"))

    for seg in edl.segments:
        clip = index.get(seg.source, base)
        src_path = seg.source_path(base)
        if clip is None and not src_path.is_file():
            errors.append(
                ValidationIssue(
                    code="missing_file",
                    message=f"source file not found: {seg.source}",
                    segment_id=seg.id,
                )
            )
            continue
        duration = clip.duration_s if clip else _probe_duration(src_path)
        if duration is None:
            errors.append(
                ValidationIssue(
                    code="missing_file",
                    message=f"cannot probe source: {seg.source}",
                    segment_id=seg.id,
                )
            )
            continue
        if seg.in_s < -1e-3 or seg.out_s > duration + 0.05:
            errors.append(
                ValidationIssue(
                    code="out_of_range",
                    message=f"in/out {seg.in_s:.3f}-{seg.out_s:.3f} outside clip duration {duration:.3f}s",
                    segment_id=seg.id,
                )
            )
        if seg.duration_s < MIN_SEGMENT_S:
            errors.append(
                ValidationIssue(
                    code="too_short",
                    message=f"segment {seg.duration_s:.3f}s is under {MIN_SEGMENT_S}s",
                    segment_id=seg.id,
                )
            )
        if check_words and clip:
            for t, label in ((seg.in_s, "in"), (seg.out_s, "out")):
                word = _inside_word(clip.words, t)
                if word:
                    errors.append(
                        ValidationIssue(
                            code="mid_word",
                            message=(
                                f"{label} cut at {t:.3f}s lands inside word "
                                f"'{word.word}' ({word.start:.3f}-{word.end:.3f})"
                            ),
                            segment_id=seg.id,
                        )
                    )
        key = str(src_path)
        for other_src, a, b, other_id in used_ranges:
            if other_src == key and _overlap(seg.in_s, seg.out_s, a, b):
                errors.append(
                    ValidationIssue(
                        code="overlap_duplicate",
                        message=f"range overlaps {other_id} ({a:.3f}-{b:.3f})",
                        segment_id=seg.id,
                    )
                )
        used_ranges.append((key, seg.in_s, seg.out_s, seg.id))
        if check_order:
            shot_at = clip.shot_at if clip else None
            if shot_at is not None:
                order = (shot_at, seg.in_s)
                if prev_order and order < prev_order:
                    errors.append(
                        ValidationIssue(
                            code="order",
                            message="segment is out of shooting order",
                            segment_id=seg.id,
                        )
                    )
                prev_order = order

    if check_target and edl.target_duration_s > 0 and edl.segments:
        total = edl.duration_s
        delta = abs(total - edl.target_duration_s) / edl.target_duration_s
        if delta > TARGET_TOLERANCE:
            errors.append(
                ValidationIssue(
                    code="target_duration",
                    message=(
                        f"duration {total:.2f}s is more than {TARGET_TOLERANCE:.0%} off "
                        f"target {edl.target_duration_s:.2f}s"
                    ),
                )
            )

    return ValidationResult(ok=not errors, errors=errors)


def _overlap(a0: float, a1: float, b0: float, b1: float) -> bool:
    return min(a1, b1) - max(a0, b0) > 1e-3


def _inside_word(words: list[Word], t: float, epsilon: float = 0.02) -> Word | None:
    for w in words:
        if w.start + epsilon < t < w.end - epsilon:
            return w
    return None


def _probe_duration(path: Path) -> float | None:
    if not path.is_file():
        return None
    try:
        from ave.ffmpeg import probe

        data = probe(path)
        return float(data.get("format", {}).get("duration") or 0) or None
    except Exception:
        return None


def index_from_analyses(analyses: list[dict], base: Path | None = None) -> MediaIndex:
    idx = MediaIndex()
    for a in analyses:
        path = Path(a["path"])
        if base and not path.is_absolute():
            path = base / path
        shot_at = None
        raw = a.get("shot_at")
        if raw:
            try:
                shot_at = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            except ValueError:
                shot_at = None
        words = [
            Word(word=w["word"], start=float(w["start"]), end=float(w["end"]))
            for w in a.get("transcript", {}).get("words", [])
        ]
        dur = float(a.get("probe", {}).get("duration_s") or 0)
        idx.add(ClipInfo(path=path, duration_s=dur, shot_at=shot_at, words=words))
    return idx


def index_from_paths(paths: list[Path]) -> MediaIndex:
    from ave.analysis.probe import probe_file
    from ave.analysis.timestamps import shot_timestamp

    idx = MediaIndex()
    for path in paths:
        meta = probe_file(path)
        idx.add(
            ClipInfo(
                path=path.resolve(),
                duration_s=meta["duration_s"],
                shot_at=shot_timestamp(path, meta),
            )
        )
    return idx
