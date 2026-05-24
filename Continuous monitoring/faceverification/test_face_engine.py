"""
tests/test_face_engine.py
--------------------------
Unit tests for FaceAuthEngine using synthetic numpy arrays.
Run with:  pytest tests/ -v
"""

from __future__ import annotations

import numpy as np
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

# We import the module under test
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from face_engine import FaceAuthEngine, AuthStatus, FaceAuthResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _blank_frame(h=480, w=640) -> np.ndarray:
    """Return a solid gray BGR frame."""
    return np.full((h, w, 3), 128, dtype=np.uint8)


def _make_engine_no_reference(tmp_path) -> FaceAuthEngine:
    """Engine with an empty reference dir."""
    ref_dir = tmp_path / "empty_ref"
    ref_dir.mkdir()
    return FaceAuthEngine(reference_dir=ref_dir)


# ---------------------------------------------------------------------------
# Reference loading
# ---------------------------------------------------------------------------

class TestReferenceLoading:

    def test_missing_reference_dir(self, tmp_path):
        engine = FaceAuthEngine(reference_dir=tmp_path / "nonexistent")
        assert not engine.is_ready
        assert engine._load_status == AuthStatus.REFERENCE_LOAD_ERROR

    def test_empty_reference_dir(self, tmp_path):
        ref = tmp_path / "ref"
        ref.mkdir()
        engine = FaceAuthEngine(reference_dir=ref)
        assert not engine.is_ready
        assert engine._load_status == AuthStatus.NO_REFERENCE

    def test_no_reference_returns_correct_status(self, tmp_path):
        engine = _make_engine_no_reference(tmp_path)
        result = engine.verify_frame(_blank_frame())
        assert result.status in (AuthStatus.NO_REFERENCE, AuthStatus.REFERENCE_LOAD_ERROR)
        assert not result.authorised


# ---------------------------------------------------------------------------
# verify_frame – mocked face_recognition
# ---------------------------------------------------------------------------

class TestVerifyFrame:

    def _engine_with_fake_encodings(self, tmp_path) -> FaceAuthEngine:
        """Engine that has one synthetic reference encoding."""
        ref = tmp_path / "ref"
        ref.mkdir()
        engine = FaceAuthEngine.__new__(FaceAuthEngine)
        engine.reference_dir = ref
        engine.tolerance = 0.50
        engine.model = "hog"
        engine.upsample = 1
        engine.min_face_area_ratio = 0.005
        engine._reference_images_loaded = 1
        engine._load_status = AuthStatus.AUTHORISED
        engine._reference_encodings = [np.zeros(128)]  # synthetic encoding
        return engine

    def test_no_face_detected(self, tmp_path):
        engine = self._engine_with_fake_encodings(tmp_path)
        with patch("face_engine.face_recognition.face_locations", return_value=[]):
            result = engine.verify_frame(_blank_frame())
        assert result.status == AuthStatus.NO_FACE
        assert not result.authorised
        assert result.faces_detected == 0

    def test_multiple_faces_rejected(self, tmp_path):
        engine = self._engine_with_fake_encodings(tmp_path)
        fake_locations = [(10, 100, 80, 30), (10, 300, 80, 230)]
        with patch("face_engine.face_recognition.face_locations", return_value=fake_locations):
            result = engine.verify_frame(_blank_frame())
        assert result.status == AuthStatus.MULTIPLE_FACES
        assert not result.authorised
        assert result.faces_detected == 2

    def test_authorised_face(self, tmp_path):
        engine = self._engine_with_fake_encodings(tmp_path)
        fake_location = [(50, 200, 150, 100)]  # (top, right, bottom, left)
        # Distance 0 = perfect match
        matching_encoding = [np.zeros(128)]

        with patch("face_engine.face_recognition.face_locations", return_value=fake_location), \
             patch("face_engine.face_recognition.face_encodings", return_value=matching_encoding), \
             patch("face_engine.face_recognition.face_distance", return_value=np.array([0.0])):
            result = engine.verify_frame(_blank_frame())

        assert result.status == AuthStatus.AUTHORISED
        assert result.authorised
        assert result.confidence == pytest.approx(1.0)

    def test_unauthorised_face(self, tmp_path):
        engine = self._engine_with_fake_encodings(tmp_path)
        fake_location = [(50, 200, 150, 100)]
        stranger_encoding = [np.ones(128)]

        with patch("face_engine.face_recognition.face_locations", return_value=fake_location), \
             patch("face_engine.face_recognition.face_encodings", return_value=stranger_encoding), \
             patch("face_engine.face_recognition.face_distance", return_value=np.array([0.80])):
            result = engine.verify_frame(_blank_frame())

        assert result.status == AuthStatus.UNAUTHORISED
        assert not result.authorised
        assert result.confidence == pytest.approx(0.20, abs=0.001)

    def test_latency_is_populated(self, tmp_path):
        engine = self._engine_with_fake_encodings(tmp_path)
        with patch("face_engine.face_recognition.face_locations", return_value=[]):
            result = engine.verify_frame(_blank_frame())
        assert result.latency_ms >= 0

    def test_small_face_filtered_out(self, tmp_path):
        engine = self._engine_with_fake_encodings(tmp_path)
        # 1x1 face in a 640x480 frame → area ratio ≈ 0.0000033, below min 0.005
        tiny_location = [(0, 1, 1, 0)]
        with patch("face_engine.face_recognition.face_locations", return_value=tiny_location):
            result = engine.verify_frame(_blank_frame())
        # Filtered to zero valid faces
        assert result.status == AuthStatus.NO_FACE

    def test_to_dict_serialisable(self, tmp_path):
        engine = self._engine_with_fake_encodings(tmp_path)
        with patch("face_engine.face_recognition.face_locations", return_value=[]):
            result = engine.verify_frame(_blank_frame())
        d = result.to_dict()
        import json
        json.dumps(d)  # must not raise


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:

    def test_verify_missing_image_path(self, tmp_path):
        engine = FaceAuthEngine(reference_dir=tmp_path / "ref")
        result = engine.verify_image_path(tmp_path / "nonexistent.jpg")
        assert not result.authorised

    def test_result_status_name_in_dict(self, tmp_path):
        engine = FaceAuthEngine(reference_dir=tmp_path / "ref")
        result = engine.verify_frame(_blank_frame())
        assert isinstance(result.to_dict()["status"], str)
