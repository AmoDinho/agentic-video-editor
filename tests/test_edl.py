from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from ave.edl.schema import EDL, Segment
from ave.edl.validator import ClipInfo, MediaIndex, Word, validate_edl


def _index(path: Path, duration: float = 10.0, words=None, shot_at=None) -> MediaIndex:
    idx = MediaIndex()
    idx.add(
        ClipInfo(
            path=path,
            duration_s=duration,
            shot_at=shot_at or datetime(2026, 1, 1, tzinfo=timezone.utc),
            words=words or [],
        )
    )
    return idx


def _edl(segments, target=4.0) -> EDL:
    return EDL(project_id="t", target_duration_s=target, segments=segments)


def test_too_short(tmp_path: Path):
    src = tmp_path / "a.mp4"
    src.write_bytes(b"x")
    edl = _edl(
        [
            Segment(
                id="seg_001",
                source=str(src),
                in_s=0,
                out_s=0.1,
                role="b_roll",
                reason="tiny",
            )
        ]
    )
    result = validate_edl(edl, _index(src), check_target=False)
    assert not result.ok
    assert any(e.code == "too_short" for e in result.errors)


def test_missing_file(tmp_path: Path):
    edl = _edl(
        [
            Segment(
                id="seg_001",
                source=str(tmp_path / "nope.mp4"),
                in_s=0,
                out_s=1,
                role="b_roll",
                reason="gone",
            )
        ]
    )
    result = validate_edl(edl, MediaIndex(), check_target=False, check_order=False)
    assert any(e.code == "missing_file" for e in result.errors)


def test_mid_word(tmp_path: Path):
    src = tmp_path / "a.mp4"
    src.write_bytes(b"x")
    words = [Word(word="hello", start=1.0, end=1.4)]
    edl = _edl(
        [
            Segment(
                id="seg_001",
                source=str(src),
                in_s=1.2,
                out_s=2.5,
                role="a_roll",
                reason="cut in word",
            )
        ]
    )
    result = validate_edl(edl, _index(src, words=words), check_target=False)
    assert any(e.code == "mid_word" for e in result.errors)


def test_duplicate_range(tmp_path: Path):
    src = tmp_path / "a.mp4"
    src.write_bytes(b"x")
    edl = _edl(
        [
            Segment(id="seg_001", source=str(src), in_s=0, out_s=2, role="b_roll", reason="a"),
            Segment(id="seg_002", source=str(src), in_s=1, out_s=3, role="b_roll", reason="b"),
        ]
    )
    result = validate_edl(edl, _index(src), check_target=False, check_order=False)
    assert any(e.code == "overlap_duplicate" for e in result.errors)


def test_target_tolerance(tmp_path: Path):
    src = tmp_path / "a.mp4"
    src.write_bytes(b"x")
    edl = _edl(
        [Segment(id="seg_001", source=str(src), in_s=0, out_s=2, role="b_roll", reason="short")],
        target=10,
    )
    result = validate_edl(edl, _index(src), check_order=False)
    assert any(e.code == "target_duration" for e in result.errors)


def test_reason_required():
    try:
        Segment(id="x", source="a.mp4", in_s=0, out_s=1, role="b_roll", reason="  ")
        assert False
    except Exception:
        assert True
