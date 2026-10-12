from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from ave.analysis.embeddings import cosine, embed_text
from ave.edl.schema import EDL
from ave.edl.validator import index_from_analyses, validate_edl
from ave.eval.metrics import evaluate
from ave.heuristic.assembler import snap_to_boundary_values

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "get_style_profile",
            "description": "Reference pacing numbers and plain-English summary",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_clips",
            "description": "Every source with duration, shot count, speech share, quality summary",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_clip_detail",
            "description": "Shots with timestamps, captions, quality scores, transcript",
            "parameters": {
                "type": "object",
                "properties": {"clip_id": {"type": "string"}},
                "required": ["clip_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_shots",
            "description": "Top shots by CLIP + caption similarity to a text query",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "k": {"type": "integer", "default": 8},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_transcript",
            "description": "Words with timestamps for a clip range",
            "parameters": {
                "type": "object",
                "properties": {
                    "clip_id": {"type": "string"},
                    "start": {"type": "number"},
                    "end": {"type": "number"},
                },
                "required": ["clip_id", "start", "end"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "snap_to_boundary",
            "description": "Nearest safe cut point (sentence end, silence, or shot change)",
            "parameters": {
                "type": "object",
                "properties": {
                    "clip_id": {"type": "string"},
                    "time": {"type": "number"},
                },
                "required": ["clip_id", "time"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "submit_edl",
            "description": "Validate an EDL. Returns pass or a list of specific errors.",
            "parameters": {
                "type": "object",
                "properties": {"edl": {"type": "object"}},
                "required": ["edl"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "evaluate_edl",
            "description": "Pacing distance to reference, runtime, dead air, duplicates, coverage",
            "parameters": {
                "type": "object",
                "properties": {"edl": {"type": "object"}},
                "required": ["edl"],
            },
        },
    },
]


class ToolBox:
    def __init__(
        self,
        analyses: list[dict[str, Any]],
        style: dict[str, Any],
        *,
        project_id: str,
        target_duration_s: float,
        locked_ids: set[str] | None = None,
        log: Callable[[dict[str, Any]], None] | None = None,
    ):
        self.analyses = analyses
        self.style = style
        self.project_id = project_id
        self.target_duration_s = target_duration_s
        self.locked_ids = locked_ids or set()
        self.log = log or (lambda _: None)
        self.last_valid: EDL | None = None
        self._by_id = {self._clip_id(a): a for a in analyses if a.get("path")}

    def _clip_id(self, a: dict[str, Any]) -> str:
        return a.get("file_hash", Path(a["path"]).stem)[:12]

    def dispatch(self, name: str, args: dict[str, Any]) -> Any:
        fn = getattr(self, name, None)
        if not fn:
            return {"error": f"unknown tool {name}"}
        result = fn(**args) if args else fn()
        self.log({"tool": name, "args": _preview(args), "result": _preview(result)})
        return result

    def get_style_profile(self) -> dict[str, Any]:
        return self.style

    def list_clips(self) -> list[dict[str, Any]]:
        rows = []
        for a in self.analyses:
            if a.get("status") == "error":
                continue
            shots = a.get("shots") or []
            rejects = sum(1 for s in shots if (s.get("quality") or {}).get("reject"))
            speech = sum(s.get("speech_share") or 0 for s in shots) / max(len(shots), 1)
            rows.append(
                {
                    "clip_id": self._clip_id(a),
                    "path": a["path"],
                    "name": Path(a["path"]).name,
                    "duration_s": a.get("probe", {}).get("duration_s"),
                    "shot_count": len(shots),
                    "speech_share": round(speech, 3),
                    "rejected_shots": rejects,
                    "shot_at": a.get("shot_at"),
                }
            )
        rows.sort(key=lambda r: r.get("shot_at") or "")
        return rows

    def get_clip_detail(self, clip_id: str) -> dict[str, Any]:
        a = self._clip(clip_id)
        if not a:
            return {"error": "unknown clip"}
        shots = []
        for s in a.get("shots") or []:
            item = {
                "id": s.get("id"),
                "in_s": s.get("in_s"),
                "out_s": s.get("out_s"),
                "role_hint": s.get("role_hint"),
                "quality": s.get("quality"),
                "speech_share": s.get("speech_share"),
                "captions": s.get("captions"),
                "loudness_lufs": s.get("loudness_lufs"),
            }
            shots.append(item)
        text = a.get("transcript", {}).get("text") or ""
        return {
            "clip_id": clip_id,
            "path": a["path"],
            "shots": shots,
            "transcript": text[:4000],
        }

    def search_shots(self, query: str, k: int = 8) -> list[dict[str, Any]]:
        qvec = embed_text(query)
        scored: list[tuple[float, dict[str, Any]]] = []
        qwords = set(query.lower().split())
        for a in self.analyses:
            for s in a.get("shots") or []:
                score = 0.0
                if qvec and s.get("embedding"):
                    score = cosine(qvec, s["embedding"])
                captions = " ".join(c.get("text", "") for c in s.get("captions") or []).lower()
                overlap = len(qwords & set(captions.split())) / max(len(qwords), 1)
                score = max(score, overlap)
                scored.append(
                    (
                        score,
                        {
                            "clip_id": self._clip_id(a),
                            "path": a["path"],
                            "shot_id": s.get("id"),
                            "in_s": s.get("in_s"),
                            "out_s": s.get("out_s"),
                            "captions": s.get("captions"),
                            "role_hint": s.get("role_hint"),
                            "score": round(score, 4),
                        },
                    )
                )
        scored.sort(key=lambda x: x[0], reverse=True)
        return [row for _, row in scored[:k]]

    def get_transcript(self, clip_id: str, start: float, end: float) -> list[dict[str, Any]]:
        a = self._clip(clip_id)
        if not a:
            return []
        words = a.get("transcript", {}).get("words") or []
        return [w for w in words if float(w["end"]) >= start and float(w["start"]) <= end]

    def snap_to_boundary(self, clip_id: str, time: float) -> dict[str, Any]:
        a = self._clip(clip_id)
        if not a:
            return {"error": "unknown clip", "time": time}
        shot = None
        for s in a.get("shots") or []:
            if s["in_s"] - 0.05 <= time <= s["out_s"] + 0.05:
                shot = dict(s)
                break
        if shot is None and a.get("shots"):
            shot = dict(min(a["shots"], key=lambda s: min(abs(s["in_s"] - time), abs(s["out_s"] - time))))
        if shot is None:
            return {"time": time}
        shot["words"] = a.get("transcript", {}).get("words") or []
        shot["vad"] = a.get("vad") or {}
        snapped = snap_to_boundary_values(shot, time)
        return {"time": snapped, "requested": time}

    def submit_edl(self, edl: dict[str, Any]) -> dict[str, Any]:
        try:
            obj = EDL.model_validate(edl)
        except Exception as exc:
            return {"ok": False, "errors": [{"code": "schema", "message": str(exc)}]}
        if not obj.project_id:
            obj.project_id = self.project_id
        if not obj.target_duration_s:
            obj.target_duration_s = self.target_duration_s
        idx = index_from_analyses(self.analyses)
        result = validate_edl(obj, idx)
        if result.ok:
            self.last_valid = obj
        return json.loads(result.model_dump_json())

    def evaluate_edl(self, edl: dict[str, Any]) -> dict[str, Any]:
        try:
            obj = EDL.model_validate(edl)
        except Exception as exc:
            return {"error": str(exc)}
        return evaluate(obj, self.analyses, self.style)

    def _clip(self, clip_id: str) -> dict[str, Any] | None:
        if clip_id in self._by_id:
            return self._by_id[clip_id]
        for a in self.analyses:
            if clip_id in {self._clip_id(a), Path(a.get("path", "")).name, a.get("path", "")}:
                return a
        return None


def _preview(obj: Any, limit: int = 1200) -> Any:
    try:
        text = json.dumps(obj, default=str)
    except Exception:
        text = str(obj)
    if len(text) > limit:
        return text[:limit] + "…"
    return obj
