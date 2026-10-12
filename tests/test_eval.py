from __future__ import annotations

from ave.edl.schema import EDL, Segment
from ave.eval.metrics import evaluate


def test_metrics_runtime_error():
    edl = EDL(
        project_id="t",
        target_duration_s=10,
        segments=[
            Segment(id="seg_001", source="a.mp4", in_s=0, out_s=2, role="b_roll", reason="x"),
        ],
    )
    stats = evaluate(edl, [], {"cuts_per_minute": 12, "shot_length": {"median": 2}})
    assert stats["runtime_error"] > 0.1
    assert stats["segment_count"] == 1
