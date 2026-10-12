from ave.edl.schema import EDL, OutputSpec, Segment
from ave.versions import keep_locked, redo, restore, save_version, strike_words, undo


def _edl(segments: list[Segment]) -> EDL:
    return EDL(project_id="p", output=OutputSpec(), target_duration_s=30, segments=segments)


def _seg(seg_id: str, *, locked: bool = False, start: float = 0, end: float = 2) -> Segment:
    return Segment(
        id=seg_id,
        source="/clips/IMG_1.MOV",
        in_s=start,
        out_s=end,
        role="a_roll",
        reason="Kept the sentence whole",
        locked=locked,
    )


def test_undo_redo_and_restore(tmp_path):
    first = _edl([_seg("a")])
    second = _edl([_seg("a"), _seg("b", start=3, end=6)])
    save_version(tmp_path, first, summary="First cuts generated", author="Agent")
    save_version(tmp_path, second, summary="Shorter intro", author="You")
    assert undo(tmp_path).duration_s == first.duration_s
    assert redo(tmp_path).duration_s == second.duration_s
    assert restore(tmp_path, 1).segments[0].id == "a"


def test_locked_segment_survives_a_regeneration():
    previous = _edl([_seg("locked", locked=True, start=1, end=4), _seg("other", start=5, end=8)])
    regenerated = _edl([_seg("other", start=5, end=8)])
    kept = keep_locked(previous, regenerated)
    assert any(segment.locked for segment in kept.segments)
    assert any(segment.id == "locked" for segment in kept.segments)


def test_striking_words_shortens_the_segment():
    edl = _edl([_seg("talk", start=0, end=6)])
    words = [
        {"start": 0.0, "end": 0.4, "word": "um"},
        {"start": 0.5, "end": 4.0, "word": "we left at six"},
        {"start": 4.2, "end": 6.0, "word": "and it's"},
    ]
    updated = strike_words(edl, "talk", words, {0, 2})
    assert updated.segments[0].in_s == 0.5
    assert updated.segments[0].out_s == 4.0
