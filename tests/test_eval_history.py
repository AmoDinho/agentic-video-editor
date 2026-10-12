from ave.analysis.probe import probe_file
from ave.edl.schema import EDL, OutputSpec, Segment
from ave.eval.history import record, regressed
from ave.eval.metrics import evaluate


def test_scores_are_tracked_and_a_regression_is_named(tmp_path):
    path = tmp_path / "scores.json"
    record(path, "sample", {"pacing_distance": 0.1, "runtime_error": 0.02, "dead_air_s": 0.4})
    record(path, "sample", {"pacing_distance": 0.4, "runtime_error": 0.02, "dead_air_s": 0.4})
    assert regressed(path, "sample") == ["pacing_distance"]


def test_evaluate_reports_the_named_scores():
    edl = EDL(
        project_id="p",
        output=OutputSpec(),
        target_duration_s=4,
        segments=[Segment(id="a", source="/a.mp4", in_s=0, out_s=4, role="b_roll", reason="Scenic hold")],
    )
    scores = evaluate(edl, [], {"cuts_per_minute": 9, "shot_length": {"median": 4}})
    for key in ("pacing_distance", "dead_air_s", "rejected_shot_count", "duplicates", "runtime_error"):
        assert key in scores


def test_probe_flags_missing_audio_and_variable_frame_rate(tmp_path):
    from ave.ffmpeg import run

    silent = tmp_path / "silent.mp4"
    run(["-f", "lavfi", "-i", "testsrc2=size=320x180:rate=30:duration=1", "-an", str(silent)], timeout=30)
    probed = probe_file(silent)
    assert probed["has_audio"] is False
    assert "is_vfr" in probed
