from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field


def expand(path: str | Path) -> Path:
    return Path(path).expanduser().resolve()


class PathsConfig(BaseModel):
    cache_dir: str = "~/.cache/ave"
    projects_dir: str = "~/.local/share/ave/projects"

    @property
    def cache(self) -> Path:
        p = expand(self.cache_dir)
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def projects(self) -> Path:
        p = expand(self.projects_dir)
        p.mkdir(parents=True, exist_ok=True)
        return p


class LLMConfig(BaseModel):
    provider: Literal["ollama", "anthropic", "openai", "openai_compatible"] = "ollama"
    model: str = "qwen2.5:7b-instruct"
    vision_model: str = "qwen2.5vl:3b"
    base_url: str = "http://localhost:11434"
    api_key_env: str | None = None
    max_iterations: int = 4
    max_tokens_per_run: int = 200000


class RenderConfig(BaseModel):
    preview_height: int = 540
    preview_encoder: str = "h264_videotoolbox"
    final_encoder: str = "libx264"
    audio_fade_ms: int = 15
    loudnorm_lufs: float = -14.0
    default_width: int = 1920
    default_height: int = 1080
    default_fps: float = 30.0
    default_audio_rate: int = 48000


class AnalysisConfig(BaseModel):
    min_shot_s: float = 0.3
    whisper_model: str = "large-v3-turbo"
    clip_model: str = "ViT-B-32"
    vad_threshold: float = 0.5
    scene_threshold: float = 27.0
    max_dead_air_s: float = 1.5


class AppConfig(BaseModel):
    paths: PathsConfig = Field(default_factory=PathsConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    render: RenderConfig = Field(default_factory=RenderConfig)
    analysis: AnalysisConfig = Field(default_factory=AnalysisConfig)


CONFIG_CANDIDATES = (
    Path("ave.yaml"),
    Path("config.yaml"),
    expand("~/.config/ave/config.yaml"),
)


def load_config(path: str | Path | None = None) -> AppConfig:
    if path:
        data = _read_yaml(expand(path))
        return AppConfig.model_validate(data)
    for candidate in CONFIG_CANDIDATES:
        if candidate.is_file():
            return AppConfig.model_validate(_read_yaml(candidate))
    return AppConfig()


def _read_yaml(path: Path) -> dict[str, Any]:
    with path.open() as f:
        return yaml.safe_load(f) or {}
