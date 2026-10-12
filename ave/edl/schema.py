from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class OutputSpec(BaseModel):
    width: int = 1920
    height: int = 1080
    fps: float = 30.0
    audio_rate: int = 48000


class Segment(BaseModel):
    id: str
    source: str
    in_s: float
    out_s: float
    audio: Literal["source"] = "source"
    role: Literal["a_roll", "b_roll"]
    reason: str
    locked: bool = False

    @field_validator("reason")
    @classmethod
    def reason_required(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("reason is required")
        return v.strip()

    @model_validator(mode="after")
    def times_ordered(self) -> Segment:
        if self.out_s <= self.in_s:
            raise ValueError("out_s must be greater than in_s")
        return self

    @property
    def duration_s(self) -> float:
        return self.out_s - self.in_s

    def source_path(self, base: Path | None = None) -> Path:
        p = Path(self.source)
        if p.is_absolute():
            return p
        if base:
            return (base / p).resolve()
        return p.resolve()


class EDL(BaseModel):
    version: Literal[1] = 1
    project_id: str
    output: OutputSpec = Field(default_factory=OutputSpec)
    target_duration_s: float
    segments: list[Segment]
    notes: str = ""

    @property
    def duration_s(self) -> float:
        return sum(s.duration_s for s in self.segments)

    def resolved(self, base: Path | None = None) -> EDL:
        segs = []
        for s in self.segments:
            data = s.model_dump()
            data["source"] = str(s.source_path(base))
            segs.append(Segment.model_validate(data))
        return self.model_copy(update={"segments": segs})

    @classmethod
    def load(cls, path: str | Path) -> EDL:
        return cls.model_validate_json(Path(path).read_text())

    def save(self, path: str | Path) -> None:
        Path(path).write_text(self.model_dump_json(indent=2))
