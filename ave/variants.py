"""Three cuts from the same footage, in shooting order.

Tight shortens scenic shots. Matched follows the style. Relaxed lets them
breathe. Every cut goes through the validator. A cut that fails is not offered.
"""

from __future__ import annotations

from typing import Any

from ave.edl.schema import Segment
from ave.edl.validator import index_from_analyses, validate_edl
from ave.heuristic.assembler import assemble

VARIANTS = ("tight", "matched", "relaxed")


def build_variants(
    analyses: list[dict[str, Any]],
    style: dict[str, Any],
    *,
    project_id: str,
    target_duration_s: float,
    locked: list[Segment] | None = None,
) -> list[dict[str, Any]]:
    index = index_from_analyses(analyses)
    cuts: list[dict[str, Any]] = []
    for name in VARIANTS:
        scale = {"tight": 0.72, "matched": 1.0, "relaxed": 1.28}[name]
        edl = assemble(
            analyses,
            style,
            project_id=f"{project_id}-{name}",
            target_duration_s=target_duration_s * scale,
            locked=locked,
            tightness=name,
        )
        result = validate_edl(edl, index, check_target=False)
        if not result.ok:
            continue
        cuts.append(
            {
                "name": name,
                "title": name.capitalize(),
                "runtime_s": round(edl.duration_s, 1),
                "cuts": len(edl.segments),
                "edl": edl.model_dump(),
                "passed": True,
            }
        )
    return cuts


def variant_plan(section_count: int) -> list[dict[str, str]]:
    steps = [{"id": "outline", "label": f"Outline: {section_count} sections from shooting order", "status": "pending"}]
    for index in range(1, section_count + 1):
        steps.append({"id": f"section-{index}", "label": f"Section {index} of {section_count}", "status": "pending"})
    steps.append({"id": "variants", "label": "Build Tight and Relaxed", "status": "pending"})
    return steps
