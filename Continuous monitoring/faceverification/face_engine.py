"""
face_engine.py
--------------
Core face recognition engine.
Responsibilities:
  - Load & encode reference images from a folder
  - Verify a single frame: exactly one face, matches the authorised person
  - Return structured FaceAuthResult for every check
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import List, Optional, Tuple

import cv2
import face_recognition
import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------

class AuthStatus(Enum):
    AUTHORISED          = auto()   # exactly one face, matches reference
    NO_FACE             = auto()   # no face detected in frame
    MULTIPLE_FACES      = auto()   # more than one face in frame
    UNAUTHORISED        = auto()   # face found but does NOT match reference
    NO_REFERENCE        = auto()   # reference folder empty / no valid encodings
    REFERENCE_LOAD_ERROR = auto()  # could not load reference images


@dataclass
class FaceLocation:
    top: int
    right: int
    bottom: int
    left: int

    @property
    def width(self) -> int:
        return self.right - self.left

    @property
    def height(self) -> int:
        return self.bottom - self.top


@dataclass
class FaceAuthResult:
    status: AuthStatus
    authorised: bool                        = False
    message: str                            = ""
    faces_detected: int                     = 0
    confidence: Optional[float]             = None   # 0-1, higher = more similar
    face_location: Optional[FaceLocation]   = None
    latency_ms: float                       = 0.0
    timestamp: float                        = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "status": self.status.name,
            "authorised": self.authorised,
            "message": self.message,
            "faces_detected": self.faces_detected,
            "confidence": round(self.confidence, 4) if self.confidence is not None else None,
            "face_location": vars(self.face_location) if self.face_location else None,
            "latency_ms": round(self.latency_ms, 2),
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class FaceAuthEngine:
    """
    Industry-grade, single-person face authorisation engine.

    Parameters
    ----------
    reference_dir : str | Path
        Directory that contains reference images of the ONE authorised person.
        Supported formats: .jpg, .jpeg, .png, .bmp, .tiff, .webp
    tolerance : float
        Face-distance threshold. Lower = stricter. Default 0.50 is recommended
        for security-sensitive deployments (face_recognition default is 0.6).
    model : str
        Detection model – "hog" (CPU-fast) or "cnn" (GPU-accurate).
    upsample : int
        How many times to upsample when detecting faces. Higher catches
        small faces but is slower.
    min_face_area_ratio : float
        Reject faces whose area is below this fraction of the total frame area
        (filters out tiny background faces).
    """

    SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"}

    def __init__(
        self,
        reference_dir: str | Path,
        tolerance: float = 0.50,
        model: str = "hog",
        upsample: int = 1,
        min_face_area_ratio: float = 0.005,
    ) -> None:
        self.reference_dir = Path(reference_dir)
        self.tolerance = tolerance
        self.model = model
        self.upsample = upsample
        self.min_face_area_ratio = min_face_area_ratio

        self._reference_encodings: List[np.ndarray] = []
        self._reference_images_loaded: int = 0
        self._load_status: AuthStatus = AuthStatus.NO_REFERENCE

        self._load_reference_images()

    # ------------------------------------------------------------------
    # Reference loading
    # ------------------------------------------------------------------

    def _load_reference_images(self) -> None:
        """Load all reference images and compute 128-d face encodings."""
        if not self.reference_dir.exists():
            logger.error("Reference directory does not exist: %s", self.reference_dir)
            self._load_status = AuthStatus.REFERENCE_LOAD_ERROR
            return

        image_paths = [
            p for p in self.reference_dir.iterdir()
            if p.suffix.lower() in self.SUPPORTED_EXTENSIONS
        ]

        if not image_paths:
            logger.warning("No supported images found in reference directory: %s", self.reference_dir)
            self._load_status = AuthStatus.NO_REFERENCE
            return

        encodings: List[np.ndarray] = []
        for path in image_paths:
            enc = self._encode_reference_image(path)
            if enc is not None:
                encodings.extend(enc)
                self._reference_images_loaded += 1

        if not encodings:
            logger.error("Could not extract any face encodings from reference images.")
            self._load_status = AuthStatus.REFERENCE_LOAD_ERROR
            return

        self._reference_encodings = encodings
        self._load_status = AuthStatus.AUTHORISED   # sentinal: loaded OK
        logger.info(
            "Reference loaded: %d image(s), %d encoding(s) from '%s'",
            self._reference_images_loaded,
            len(self._reference_encodings),
            self.reference_dir,
        )

    def _encode_reference_image(self, path: Path) -> Optional[List[np.ndarray]]:
        """Return face encodings for a single reference image, or None on failure."""
        try:
            img = face_recognition.load_image_file(str(path))
            locations = face_recognition.face_locations(img, number_of_times_to_upsample=self.upsample, model=self.model)
            if not locations:
                logger.warning("No face detected in reference image: %s", path.name)
                return None
            if len(locations) > 1:
                logger.warning(
                    "Multiple faces in reference image '%s'; using all %d encodings.",
                    path.name, len(locations),
                )
            encodings = face_recognition.face_encodings(img, known_face_locations=locations, num_jitters=3)
            return encodings
        except Exception as exc:
            logger.error("Failed to process reference image '%s': %s", path.name, exc)
            return None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def is_ready(self) -> bool:
        """True when reference encodings were successfully loaded."""
        return bool(self._reference_encodings)

    def verify_frame(self, frame: np.ndarray) -> FaceAuthResult:
        """
        Verify a single BGR/RGB frame against the authorised reference.

        Parameters
        ----------
        frame : np.ndarray
            Image array (H x W x 3). OpenCV frames are BGR; pass as-is,
            conversion is handled internally.

        Returns
        -------
        FaceAuthResult
        """
        t_start = time.perf_counter()

        # Guard: reference not loaded
        if not self.is_ready:
            return FaceAuthResult(
                status=self._load_status,
                message="No valid reference encodings loaded. Provide reference images.",
                latency_ms=(time.perf_counter() - t_start) * 1000,
            )

        # Convert BGR → RGB (face_recognition expects RGB)
        rgb_frame = self._to_rgb(frame)
        frame_area = rgb_frame.shape[0] * rgb_frame.shape[1]

        # Detect faces on full resolution for maximum accuracy
        raw_locations = face_recognition.face_locations(
            rgb_frame,
            number_of_times_to_upsample=self.upsample,
            model=self.model,
        )

        # Filter out tiny faces (noise / background)
        locations = self._filter_small_faces(raw_locations, frame_area)

        latency_ms = (time.perf_counter() - t_start) * 1000

        # ── No face ──────────────────────────────────────────────────
        if len(locations) == 0:
            return FaceAuthResult(
                status=AuthStatus.NO_FACE,
                message="No face detected in the frame.",
                faces_detected=0,
                latency_ms=latency_ms,
            )

        # ── Multiple faces ───────────────────────────────────────────
        if len(locations) > 1:
            return FaceAuthResult(
                status=AuthStatus.MULTIPLE_FACES,
                message=f"Multiple faces detected ({len(locations)}). Only one person allowed in the frame.",
                faces_detected=len(locations),
                latency_ms=latency_ms,
            )

        # ── Exactly one face – compare against reference ─────────────
        face_loc = locations[0]
        encodings = face_recognition.face_encodings(rgb_frame, known_face_locations=[face_loc])

        if not encodings:
            # Unlikely but guard anyway
            return FaceAuthResult(
                status=AuthStatus.NO_FACE,
                message="Face detected but encoding failed (low quality / obstructed face).",
                faces_detected=1,
                latency_ms=latency_ms,
            )

        probe_encoding = encodings[0]
        is_match, confidence = self._match_encoding(probe_encoding)
        fl = FaceLocation(*face_loc)  # (top, right, bottom, left)

        latency_ms = (time.perf_counter() - t_start) * 1000

        if is_match:
            return FaceAuthResult(
                status=AuthStatus.AUTHORISED,
                authorised=True,
                message="Access granted. Authorised person verified.",
                faces_detected=1,
                confidence=confidence,
                face_location=fl,
                latency_ms=latency_ms,
            )
        else:
            return FaceAuthResult(
                status=AuthStatus.UNAUTHORISED,
                authorised=False,
                message="Access denied. Person does not match the authorised reference.",
                faces_detected=1,
                confidence=confidence,
                face_location=fl,
                latency_ms=latency_ms,
            )

    def verify_image_path(self, image_path: str | Path) -> FaceAuthResult:
        """Convenience wrapper: load an image file and verify it."""
        path = Path(image_path)
        if not path.exists():
            return FaceAuthResult(
                status=AuthStatus.REFERENCE_LOAD_ERROR,
                message=f"Image file not found: {path}",
            )
        try:
            frame = cv2.imread(str(path))
            if frame is None:
                raise ValueError("cv2.imread returned None")
            return self.verify_frame(frame)
        except Exception as exc:
            logger.error("Failed to read probe image '%s': %s", path, exc)
            return FaceAuthResult(
                status=AuthStatus.REFERENCE_LOAD_ERROR,
                message=f"Could not read image: {exc}",
            )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _to_rgb(self, frame: np.ndarray) -> np.ndarray:
        """Convert BGR (OpenCV) to RGB. Also handles already-RGB input gracefully."""
        if frame.ndim == 3 and frame.shape[2] == 3:
            return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        return frame

    def _filter_small_faces(
        self, locations: list, frame_area: int
    ) -> list:
        """Remove face locations whose area is below min_face_area_ratio."""
        filtered = []
        for loc in locations:
            top, right, bottom, left = loc
            face_area = (bottom - top) * (right - left)
            ratio = face_area / max(frame_area, 1)
            if ratio >= self.min_face_area_ratio:
                filtered.append(loc)
            else:
                logger.debug("Discarded tiny face (area ratio %.4f < %.4f)", ratio, self.min_face_area_ratio)
        return filtered

    def _match_encoding(self, probe: np.ndarray) -> Tuple[bool, float]:
        """
        Compare probe encoding against all reference encodings.
        Uses min distance — the authorized person will always have at
        least one reference that matches closely. Strangers won't.
        The sliding window in StreamVerifier handles occasional dips.

        Returns (is_match, confidence) where confidence = 1 - min_distance.
        """
        distances = face_recognition.face_distance(self._reference_encodings, probe)
        min_distance = float(np.min(distances))
        confidence = max(0.0, 1.0 - min_distance)
        is_match = min_distance <= self.tolerance
        logger.debug(
            "Face match check: min_distance=%.4f, tolerance=%.4f, match=%s",
            min_distance, self.tolerance, is_match,
        )
        return is_match, confidence
