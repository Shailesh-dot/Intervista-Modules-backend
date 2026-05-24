"""
stream_verifier.py
------------------
Continuous face-auth verification from a live camera / RTSP stream.
Uses a fully decoupled architecture:
  - Capture Thread: grabs frames at native camera FPS (30+)
  - Verify Thread: runs deep learning recognition bounded by fps_cap
  - Main thread (GUI): reads latest frame + result for display

Sliding window temporal smoothing prevents flickering.
"Sticky" authorization: once verified, stays authorized while tracker holds.
Dlib correlation tracker provides smooth inter-frame bounding box.
"""

from __future__ import annotations

import collections
import logging
import threading
import time
from typing import Callable, Optional

import cv2
import dlib
import numpy as np

from face_engine import FaceAuthEngine, FaceAuthResult, AuthStatus, FaceLocation

logger = logging.getLogger(__name__)

# Sliding window config
WINDOW_SIZE = 15
AUTH_GAIN_THRESHOLD = 10   # Need 10 of 15 to GAIN authorization (very strict entry)
AUTH_LOSE_THRESHOLD = 15   # ALL 15 must fail to declare UNAUTHORISED


class StreamVerifier:
    """
    Wraps FaceAuthEngine for real-time video stream verification.
    Uses multi-threading to decouple fast frame capture from heavy
    deep learning verification, with Dlib tracking for smooth boxes.
    """

    def __init__(
        self,
        engine: FaceAuthEngine,
        source: int | str = 0,
        fps_cap: float = 10.0,
        on_result: Optional[Callable[[FaceAuthResult], None]] = None,
        on_error: Optional[Callable[[Exception], None]] = None,
    ) -> None:
        self.engine = engine
        self.source = source
        self.fps_cap = max(1.0, fps_cap)
        self.on_result = on_result
        self.on_error = on_error

        self._running = False
        self._cap_thread: Optional[threading.Thread] = None
        self._ver_thread: Optional[threading.Thread] = None

        # Shared state (protected by _lock)
        self._lock = threading.Lock()
        self._latest_frame: Optional[np.ndarray] = None
        self._display_result: Optional[FaceAuthResult] = None

        # Sliding window of recent deep-learning verdicts (True=auth, False=deny)
        self._auth_window: collections.deque = collections.deque(maxlen=WINDOW_SIZE)
        self._smoothed_authorised: bool = False

        # Dlib tracker
        self._tracker: Optional[dlib.correlation_tracker] = None
        self._tracker_active: bool = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def latest_result(self) -> Optional[FaceAuthResult]:
        with self._lock:
            return self._display_result

    @property
    def latest_frame(self) -> Optional[np.ndarray]:
        with self._lock:
            if self._latest_frame is None:
                return None
            return self._latest_frame.copy()

    def start(self) -> None:
        if self._running:
            logger.warning("StreamVerifier already running.")
            return
        self._running = True
        self._cap_thread = threading.Thread(
            target=self._capture_loop, daemon=True, name="FaceCap"
        )
        self._ver_thread = threading.Thread(
            target=self._verify_loop, daemon=True, name="FaceVer"
        )
        self._cap_thread.start()
        self._ver_thread.start()
        logger.info("StreamVerifier started. Source: %s, FPS cap: %s", self.source, self.fps_cap)

    def stop(self, timeout: float = 5.0) -> None:
        self._running = False
        if self._cap_thread:
            self._cap_thread.join(timeout=timeout)
        if self._ver_thread:
            self._ver_thread.join(timeout=timeout)
        logger.info("StreamVerifier stopped.")

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *_):
        self.stop()

    # ------------------------------------------------------------------
    # Capture Thread (fast – 30+ FPS)
    # ------------------------------------------------------------------

    def _capture_loop(self) -> None:
        """Read frames as fast as possible and update Dlib tracker."""
        cap = cv2.VideoCapture(self.source)
        if not cap.isOpened():
            err = RuntimeError(f"Cannot open video source: {self.source}")
            logger.error(str(err))
            if self.on_error:
                self.on_error(err)
            self._running = False
            return

        try:
            while self._running:
                ret, frame = cap.read()
                if not ret:
                    time.sleep(0.05)
                    continue

                with self._lock:
                    self._latest_frame = frame

                    # Update Dlib tracker on each frame for smooth bounding box
                    if self._tracker_active and self._tracker is not None:
                        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        confidence = self._tracker.update(rgb)

                        if confidence < 6.0:
                            # Tracker lost the face completely
                            self._tracker_active = False
                            self._tracker = None
                            self._smoothed_authorised = False
                            self._auth_window.clear()
                            self._display_result = FaceAuthResult(
                                status=AuthStatus.NO_FACE,
                                authorised=False,
                                message="Tracking lost. Re-verifying...",
                                faces_detected=0,
                            )
                        else:
                            # Update bounding box from tracker
                            pos = self._tracker.get_position()
                            if self._display_result:
                                self._display_result.face_location = FaceLocation(
                                    top=int(pos.top()),
                                    right=int(pos.right()),
                                    bottom=int(pos.bottom()),
                                    left=int(pos.left()),
                                )

                # Small sleep to cap at ~60 FPS max and yield CPU
                time.sleep(0.005)
        finally:
            cap.release()
            logger.debug("Camera released.")

    # ------------------------------------------------------------------
    # Verification Thread (slow – bounded by fps_cap)
    # ------------------------------------------------------------------

    def _verify_loop(self) -> None:
        """Run deep-learning verification and update sliding window."""
        interval = 1.0 / self.fps_cap

        while self._running:
            t0 = time.perf_counter()

            with self._lock:
                frame = self._latest_frame.copy() if self._latest_frame is not None else None

            if frame is None:
                time.sleep(0.05)
                continue

            # Heavy computation (outside lock)
            result = self.engine.verify_frame(frame)

            with self._lock:
                # Push raw deep-learning verdict into sliding window
                if result.status == AuthStatus.AUTHORISED:
                    self._auth_window.append(True)
                elif result.status == AuthStatus.UNAUTHORISED:
                    self._auth_window.append(False)
                elif result.status == AuthStatus.MULTIPLE_FACES:
                    # Immediate full revocation on multiple faces
                    self._auth_window.clear()
                    self._smoothed_authorised = False
                    self._tracker_active = False
                    self._tracker = None
                elif result.status == AuthStatus.NO_FACE:
                    self._auth_window.append(False)

                # Asymmetric sliding window logic:
                # - Easy to GAIN auth: need AUTH_GAIN_THRESHOLD positives
                # - Hard to LOSE auth: need AUTH_LOSE_THRESHOLD negatives (sticky)
                if len(self._auth_window) > 0:
                    auth_count = sum(self._auth_window)
                    deny_count = len(self._auth_window) - auth_count

                    if not self._smoothed_authorised:
                        # Not yet authorized → need AUTH_GAIN_THRESHOLD positives
                        self._smoothed_authorised = auth_count >= AUTH_GAIN_THRESHOLD
                    else:
                        # Already authorized → only revoke if AUTH_LOSE_THRESHOLD failures
                        self._smoothed_authorised = deny_count < AUTH_LOSE_THRESHOLD

                # Build the display result with smoothed authorization
                if self._smoothed_authorised:
                    smoothed_result = FaceAuthResult(
                        status=AuthStatus.AUTHORISED,
                        authorised=True,
                        message="Access granted. Authorised person verified.",
                        faces_detected=result.faces_detected,
                        confidence=result.confidence,
                        face_location=result.face_location,
                        latency_ms=result.latency_ms,
                    )
                else:
                    auth_count = sum(self._auth_window) if self._auth_window else 0
                    deny_count = len(self._auth_window) - auth_count
                    window_full = len(self._auth_window) >= WINDOW_SIZE
                    all_failed = window_full and deny_count >= AUTH_LOSE_THRESHOLD

                    if all_failed:
                        # ALL 15 frames failed — confirmed UNAUTHORISED
                        smoothed_result = FaceAuthResult(
                            status=AuthStatus.UNAUTHORISED,
                            authorised=False,
                            message="Access denied. Unauthorised person.",
                            faces_detected=result.faces_detected,
                            confidence=result.confidence,
                            face_location=result.face_location,
                            latency_ms=result.latency_ms,
                        )
                    else:
                        # Still checking — show "Identifying..." (NOT unauthorised)
                        smoothed_result = FaceAuthResult(
                            status=AuthStatus.NO_FACE,  # neutral status
                            authorised=False,
                            message=f"Identifying... ({auth_count}/{AUTH_GAIN_THRESHOLD} of {len(self._auth_window)}/{WINDOW_SIZE})",
                            faces_detected=result.faces_detected,
                            confidence=result.confidence,
                            face_location=result.face_location,
                            latency_ms=result.latency_ms,
                        )

                # Initialize or re-sync Dlib tracker when we have a face
                if result.faces_detected == 1 and result.face_location:
                    fl = result.face_location
                    self._tracker = dlib.correlation_tracker()
                    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    rect = dlib.rectangle(fl.left, fl.top, fl.right, fl.bottom)
                    self._tracker.start_track(rgb, rect)
                    self._tracker_active = True

                    # Preserve smooth tracker position for display
                    if self._display_result and self._display_result.face_location:
                        smoothed_result.face_location = self._display_result.face_location
                    else:
                        smoothed_result.face_location = result.face_location
                else:
                    if result.status != AuthStatus.UNAUTHORISED:
                        # Only kill tracker if truly no face (not just unauthorized)
                        self._tracker_active = False
                        self._tracker = None

                # MULTIPLE_FACES takes priority over ALL other states
                if result.status == AuthStatus.MULTIPLE_FACES:
                    smoothed_result = FaceAuthResult(
                        status=AuthStatus.MULTIPLE_FACES,
                        authorised=False,
                        message="Multiple persons detected.",
                        faces_detected=result.faces_detected,
                        confidence=result.confidence,
                        face_location=result.face_location,
                        latency_ms=result.latency_ms,
                    )

                self._display_result = smoothed_result

            # Fire callback
            if self.on_result:
                try:
                    self.on_result(result)
                except Exception as cb_exc:
                    logger.error("on_result callback raised: %s", cb_exc)

            # Throttle to fps_cap
            elapsed = time.perf_counter() - t0
            sleep_for = interval - elapsed
            if sleep_for > 0:
                time.sleep(sleep_for)
