from ave.edl.schema import EDL
from ave.edl.validator import index_from_analyses, validate_edl
from ave.variants import build_variants, variant_plan


def _shot(path: str, start: float, end: float, role: str, when: str) -> dict:
    return {
        "path": path,
        "in_s": start,
        "out_s": end,
        "role_hint": role,
        "speech_share": 0.8 if role == "a_roll" else 0.0,
        "shot_at": when,
        "quality": {"reject": False},
        "words": [],
    }


def _analysis(path: str, shots: list[dict], when: str) -> dict:
    return {
        "path": path,
        "shot_at": when,
        "probe": {"duration_s": shots[-1]["out_s"], "has_audio": True},
        "shots": shots,
        "vad": {"speech": [{"start": 0.2, "end": 2.0}] if shots[0]["role_hint"] == "a_roll" else []},
        "transcript": {"words": []},
    }


def test_three_variants_pass_and_tight_is_shorter_than_relaxed():
    analyses = [
        _analysis(
            "/a/IMG_1.MOV",
            [_shot("/a/IMG_1.MOV", 0, 8, "a_roll", "2026-10-03T08:00:00")],
            "2026-10-03T08:00:00",
        ),
        _analysis(
            "/a/GOPR_1.MP4",
            [_shot("/a/GOPR_1.MP4", 0, 12, "b_roll", "2026-10-03T09:00:00")],
            "2026-10-03T09:00:00",
        ),
        _analysis(
            "/a/IMG_2.MOV",
            [_shot("/a/IMG_2.MOV", 0, 6, "a_roll", "2026-10-03T10:00:00")],
            "2026-10-03T10:00:00",
        ),
        _analysis(
            "/a/GOPR_2.MP4",
            [_shot("/a/GOPR_2.MP4", 0, 10, "b_roll", "2026-10-03T11:00:00")],
            "2026-10-03T11:00:00",
        ),
    ]
    style = {"shot_length": {"p10": 1.5, "median": 3.0, "p90": 6.0}, "summary": "About 9 cuts a minute"}
    cuts = build_variants(analyses, style, project_id="wild-coast", target_duration_s=20)
    assert [cut["name"] for cut in cuts] == ["tight", "matched", "relaxed"]
    assert all(cut["passed"] for cut in cuts)
    assert cuts[0]["runtime_s"] <= cuts[2]["runtime_s"]
    for cut in cuts:
        edl = EDL.model_validate(cut["edl"])
        result = validate_edl(edl, index_from_analyses(analyses), check_target=False, check_words=False)
        assert result.ok


def test_plan_names_sections_instead_of_guessing():
    plan = variant_plan(5)
    assert plan[0]["label"].startswith("Outline")
    assert plan[3]["label"] == "Section 3 of 5"
    assert plan[-1]["label"] == "Build Tight and Relaxed"
