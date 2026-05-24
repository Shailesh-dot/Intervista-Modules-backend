"""
config.py
---------
Central configuration with environment-variable overrides.
All tunable parameters in one place for clean production deployments.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _env(key: str, default: str) -> str:
    return os.environ.get(key, default)


@dataclass
class EngineConfig:
    # Path that holds reference images of the ONE authorised person
    reference_dir: Path = field(
        default_factory=lambda: Path(_env("FACE_AUTH_REFERENCE_DIR", "reference_images"))
    )

    # ── Detection ────────────────────────────────────────────────────
    # "hog" = faster on CPU; "cnn" = more accurate, requires GPU/dlib CUDA
    detection_model: str = field(
        default_factory=lambda: _env("FACE_AUTH_MODEL", "hog")
    )
    upsample: int = field(
        default_factory=lambda: int(_env("FACE_AUTH_UPSAMPLE", "1"))
    )

    # ── Matching ─────────────────────────────────────────────────────
    # Uses min-distance matching (closest reference wins).
    # 0.48 is slightly stricter for tighter security.
    tolerance: float = field(
        default_factory=lambda: float(_env("FACE_AUTH_TOLERANCE", "0.48"))
    )

    # Discard faces smaller than this fraction of total frame area
    min_face_area_ratio: float = field(
        default_factory=lambda: float(_env("FACE_AUTH_MIN_FACE_AREA", "0.02"))
    )

    # ── Stream ───────────────────────────────────────────────────────
    camera_source: str = field(
        default_factory=lambda: _env("FACE_AUTH_CAMERA_SOURCE", "0")
    )
    stream_fps_cap: float = field(
        default_factory=lambda: float(_env("FACE_AUTH_STREAM_FPS", "10.0"))
    )

    # ── Audit ────────────────────────────────────────────────────────
    log_dir: Path = field(
        default_factory=lambda: Path(_env("FACE_AUTH_LOG_DIR", "logs"))
    )
    actor_id: str = field(
        default_factory=lambda: _env("FACE_AUTH_ACTOR_ID", "gate-1")
    )

    # ── Logging ──────────────────────────────────────────────────────
    log_level: str = field(
        default_factory=lambda: _env("FACE_AUTH_LOG_LEVEL", "INFO")
    )

    def __post_init__(self):
        # Coerce camera_source: if it's a digit string, return int
        src = self.camera_source
        if isinstance(src, str) and src.isdigit():
            self.camera_source = int(src)  # type: ignore[assignment]
