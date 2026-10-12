from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from ave.agent.llm import LLMClient, LLMMessage
from ave.agent.tools import TOOL_SCHEMAS, ToolBox
from ave.config import AppConfig, load_config
from ave.edl.schema import EDL, Segment
from ave.heuristic.assembler import assemble

SYSTEM = """You are a local video editor. You never render video and never write FFmpeg commands.
You only inspect footage summaries via tools and produce a JSON edit decision list.

Rules:
- Segments always stay in shooting order. You choose what to keep and how long, never the sequence.
- Keep talking (A-roll) stretches whole. Never cut inside a spoken word.
- B-roll keeps its own natural sound. Trim B-roll to the reference shot-length rhythm.
- Every segment needs role (a_roll|b_roll) and a short reason.
- Target duration must land within 10%.
- Locked segments must be kept unchanged.
- Prefer snapping cuts to sentence ends, silence, or shot changes via snap_to_boundary.

Loop:
1. Read the style profile and brief; write a short outline (sections with target durations).
2. Survey clips; identify A-roll vs B-roll.
3. Walk clips in shooting order and pick segments.
4. Snap cuts, then submit_edl.
5. evaluate_edl; if pacing or runtime is off, revise the weakest sections and resubmit.
Stop when submit_edl passes and evaluate_edl is ok, or when you cannot improve further.
"""


def run_agent(
    analyses: list[dict[str, Any]],
    style: dict[str, Any],
    *,
    project_id: str,
    target_duration_s: float,
    brief: str = "",
    note: str = "",
    locked: list[Segment] | None = None,
    config: AppConfig | None = None,
    emit: Callable[[dict[str, Any]], None] | None = None,
    trace_path: Path | None = None,
) -> EDL:
    cfg = config or load_config()
    traces: list[dict[str, Any]] = []

    def log(event: dict[str, Any]) -> None:
        event = {"ts": datetime.now(timezone.utc).isoformat(), **event}
        traces.append(event)
        if emit:
            emit({"stage": "agent", **event})

    box = ToolBox(
        analyses,
        style,
        project_id=project_id,
        target_duration_s=target_duration_s,
        locked_ids={s.id for s in (locked or [])},
        log=log,
    )
    fallback = assemble(
        analyses,
        style,
        project_id=project_id,
        target_duration_s=target_duration_s,
        locked=locked,
    )
    try:
        client = LLMClient(cfg.llm)
        messages = [
            LLMMessage(role="system", content=SYSTEM),
            LLMMessage(role="user", content=_user_prompt(brief, note, locked, target_duration_s, project_id)),
        ]
        for iteration in range(cfg.llm.max_iterations + 1):
            if client.remaining_tokens() <= 0:
                log({"event": "token_cap"})
                break
            log({"event": "iteration", "n": iteration})
            try:
                reply = client.chat(messages, TOOL_SCHEMAS)
            except Exception as exc:
                log({"event": "llm_error", "error": str(exc)})
                break
            messages.append(reply)
            if not reply.tool_calls:
                if box.last_valid:
                    break
                messages.append(
                    LLMMessage(
                        role="user",
                        content="Submit an EDL with submit_edl now. Use shooting order and the target duration.",
                    )
                )
                continue
            for tc in reply.tool_calls:
                result = box.dispatch(tc.name, tc.arguments or {})
                messages.append(
                    LLMMessage(
                        role="tool",
                        name=tc.name,
                        tool_call_id=tc.id,
                        content=json.dumps(result, default=str)[:8000],
                    )
                )
            if box.last_valid:
                stats = box.evaluate_edl(json.loads(box.last_valid.model_dump_json()))
                log({"event": "evaluated", "stats": stats})
                if stats.get("ok"):
                    break
                messages.append(
                    LLMMessage(
                        role="user",
                        content="Checks are not ok yet: "
                        + json.dumps(stats)
                        + ". Revise the weakest sections and submit_edl again. Keep locked segments.",
                    )
                )
        edl = box.last_valid or fallback
    except Exception as exc:
        log({"event": "agent_failed", "error": str(exc)})
        edl = fallback
        edl.notes = f"Fell back to heuristic assembler ({exc}). " + (edl.notes or "")
    if locked:
        edl = _keep_locked(edl, locked, analyses)
    if trace_path:
        trace_path.parent.mkdir(parents=True, exist_ok=True)
        trace_path.write_text(json.dumps(traces, indent=2, default=str))
    return edl


def _user_prompt(
    brief: str,
    note: str,
    locked: list[Segment] | None,
    target: float,
    project_id: str,
) -> str:
    parts = [
        f"Project {project_id}. Target duration {target:.1f}s.",
        "Call get_style_profile and list_clips first.",
    ]
    if brief:
        parts.append(f"User brief: {brief}")
    if note:
        parts.append(f"Revision note: {note}")
    if locked:
        parts.append("Locked segments (keep exactly): " + json.dumps([s.model_dump() for s in locked]))
    return "\n".join(parts)


def _keep_locked(edl: EDL, locked: list[Segment], analyses: list[dict[str, Any]]) -> EDL:
    from ave.heuristic.assembler import _reinsert_locked

    segs = _reinsert_locked(list(edl.segments), locked, _shots(analyses))
    for i, s in enumerate(segs):
        s.id = f"seg_{i+1:03d}"
    return edl.model_copy(update={"segments": segs})


def _shots(analyses: list[dict[str, Any]]) -> list[dict[str, Any]]:
    from datetime import datetime

    out = []
    for a in analyses:
        try:
            dt = datetime.fromisoformat((a.get("shot_at") or "").replace("Z", "+00:00"))
        except ValueError:
            dt = datetime.min
        for s in a.get("shots") or []:
            item = dict(s)
            item["path"] = a["path"]
            item["shot_at"] = dt
            out.append(item)
    return out
