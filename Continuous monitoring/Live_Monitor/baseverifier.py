"""
face_verifier.py  —  Candidate Face Verification Module
=========================================================
Runs INDEPENDENTLY alongside the main gaze/device detector.

HOW IT WORKS
------------
1. On startup it loads 3-4 reference photos from a folder you specify
   (REFERENCE_DIR below). It encodes each face into a 128-d vector using
   face_recognition (dlib under the hood).

2. Every frame it reads the webcam, finds the live face, and computes
   cosine distance against the mean reference vector.

3. Visual feedback:
   • GREEN  border + "VERIFIED"       → match (distance < MATCH_THRESHOLD)
   • RED    border + "WRONG CANDIDATE"→ mismatch, logs breach start time
   • ORANGE border + "NO FACE"        → no face detected (lenient, same as main)

4. Breach escalation (mirrors main script's staged logic):
   0 – 2 s   → yellow banner "Verifying identity…"
   2 – 4 s   → orange banner "Identity mismatch – stay in frame"
   4 s+       → red banner  "WRONG CANDIDATE – flagged"
              → writes flag to shared state file so main script can read it

SHARED STATE FILE
-----------------
Path: ./verifier_state.json   (same directory as this script)
Schema:
  {
    "verified": true/false,
    "breach_elapsed": 0.0,    # seconds of continuous mismatch
    "status": "VERIFIED" | "MISMATCH" | "NO_FACE",
    "timestamp": 1700000000.0
  }

The main script can optionally import `read_verifier_state()` (bottom of
this file) to react to mismatch events.

SETUP
-----
pip install face_recognition opencv-python numpy

REFERENCE PHOTOS
----------------
Put 3-4 clear, front-facing photos of the authorised candidate in a folder.
Set REFERENCE_DIR to that folder path.
Photos can be .jpg / .jpeg / .png — any size, face_recognition handles it.

USAGE
-----
  python face_verifier.py                     # uses default REFERENCE_DIR
  python face_verifier.py --refs ./my_photos  # override reference folder
"""

import cv2
import numpy as np
import face_recognition
import json
import os
import time
import argparse
import glob
import sys
from pathlib import Path

# ── CONFIG ──────────────────────────────────────────────────────────────────
REFERENCE_DIR      = "/home/rithan/Pictures/Camera"   # ← put your 3-4 photos here
MATCH_THRESHOLD    = 0.45                   # lower = stricter  (0.45 – 0.55 typical)
STATE_FILE         = "./verifier_state.json"

# Breach stage timings (seconds)
YELLOW_END         = 2.0
ORANGE_END         = 4.0

# Frame-skip: only run recognition every N frames (perf)
RECOG_EVERY        = 5

# ── COLOURS (BGR) ───────────────────────────────────────────────────────────
GREEN  = (0, 220, 0)
RED    = (0, 0, 220)
YELLOW = (0, 220, 255)
ORANGE = (0, 140, 255)
WHITE  = (255, 255, 255)
DARK   = (20, 20, 20)

# ── SHARED STATE HELPERS ────────────────────────────────────────────────────

def write_state(verified: bool, status: str, breach_elapsed: float):
    payload = {
        "verified":       verified,
        "breach_elapsed": round(breach_elapsed, 2),
        "status":         status,
        "timestamp":      time.time(),
    }
    tmp = STATE_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(payload, f)
    os.replace(tmp, STATE_FILE)          # atomic write — no partial reads


def read_verifier_state() -> dict:
    """
    Call this from the MAIN script to get live verification status.
    Returns a dict with keys: verified, breach_elapsed, status, timestamp.
    Returns None if the file doesn't exist yet.
    """
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


# ── REFERENCE ENCODING ──────────────────────────────────────────────────────

def load_reference_encodings(folder: str) -> np.ndarray | None:
    """
    Loads all images from `folder`, extracts the first face from each,
    and returns the MEAN 128-d encoding vector.
    Returns None if no valid faces found.
    """
    patterns = ["*.jpg", "*.jpeg", "*.png", "*.JPG", "*.JPEG", "*.PNG"]
    paths = []
    for pat in patterns:
        paths.extend(glob.glob(os.path.join(folder, pat)))

    if not paths:
        print(f"[face_verifier] ERROR: No images found in '{folder}'")
        return None

    encodings = []
    for p in paths:
        img = face_recognition.load_image_file(p)
        encs = face_recognition.face_encodings(img)
        if encs:
            encodings.append(encs[0])
            print(f"[face_verifier] ✓ Loaded reference: {Path(p).name}")
        else:
            print(f"[face_verifier] ✗ No face found in: {Path(p).name} — skipping")

    if not encodings:
        print("[face_verifier] ERROR: Could not encode any reference faces.")
        return None

    mean_enc = np.mean(encodings, axis=0)
    print(f"[face_verifier] Reference vector built from {len(encodings)} photo(s).")
    return mean_enc


# ── OVERLAY HELPERS ─────────────────────────────────────────────────────────

def tinted_overlay(frame, color, alpha=0.07):
    ov = frame.copy()
    h, w = frame.shape[:2]
    cv2.rectangle(ov, (0, 0), (w, h), color, -1)
    cv2.addWeighted(ov, alpha, frame, 1 - alpha, 0, frame)


def border(frame, color, thickness=3):
    h, w = frame.shape[:2]
    cv2.rectangle(frame, (0, 0), (w - 1, h - 1), color, thickness)


def banner(frame, text, color, y=38, scale=1.0, thickness=2):
    cv2.putText(frame, text, (15, y),
                cv2.FONT_HERSHEY_SIMPLEX, scale, color, thickness)


def draw_face_box(frame, top, right, bottom, left, color, label):
    cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
    cv2.putText(frame, label, (left, top - 8),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)


# ── MAIN ────────────────────────────────────────────────────────────────────

def main(ref_dir: str):
    print("=" * 60)
    print("  Face Verifier — press Q to quit")
    print(f"  Reference folder : {ref_dir}")
    print(f"  Match threshold  : {MATCH_THRESHOLD}")
    print(f"  State file       : {STATE_FILE}")
    print("=" * 60)

    ref_enc = load_reference_encodings(ref_dir)
    if ref_enc is None:
        sys.exit(1)

    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    frame_idx         = 0
    breach_start      = None     # time when continuous mismatch started
    cached_locations  = []       # face boxes from last recognition frame
    cached_match      = True     # last match result
    cached_distance   = 0.0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame     = cv2.flip(frame, 1)
        h, w      = frame.shape[:2]
        frame_idx += 1

        # ── Dark header bar ─────────────────────────────────────────
        cv2.rectangle(frame, (0, 0), (w, 55), DARK, -1)

        # ── Face recognition (every RECOG_EVERY frames) ─────────────
        if frame_idx % RECOG_EVERY == 0:
            # Downsample for speed, then scale locations back up
            small   = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)
            rgb_small = np.ascontiguousarray(small[:, :, ::-1])   # BGR → RGB, ensure contiguous memory

            locations = face_recognition.face_locations(rgb_small, model="hog")
            # scale back
            cached_locations = [(t*2, r*2, b*2, l*2) for (t, r, b, l) in locations]

            if cached_locations:
                encs = face_recognition.face_encodings(rgb_small, known_face_locations=locations)
                if encs:
                    dist = float(np.linalg.norm(encs[0] - ref_enc))
                    cached_distance = dist
                    cached_match    = dist < MATCH_THRESHOLD
                else:
                    cached_match    = False
                    cached_distance = 1.0
            else:
                cached_match    = None   # no face
                cached_distance = 1.0

        # ── Determine current status ─────────────────────────────────
        if cached_match is None:
            status    = "NO_FACE"
            is_breach = False
        elif cached_match:
            status    = "VERIFIED"
            is_breach = False
        else:
            status    = "MISMATCH"
            is_breach = True

        # ── Draw face boxes ──────────────────────────────────────────
        for (top, right, bottom, left) in cached_locations:
            if cached_match is None:
                box_color = YELLOW
                box_label = "No Face"
            elif cached_match:
                box_color = GREEN
                box_label = f"VERIFIED  d={cached_distance:.3f}"
            else:
                box_color = RED
                box_label = f"MISMATCH  d={cached_distance:.3f}"
            draw_face_box(frame, top, right, bottom, left, box_color, box_label)

        # ── Breach timer ─────────────────────────────────────────────
        now = time.time()
        if is_breach:
            if breach_start is None:
                breach_start = now
            elapsed = now - breach_start
        else:
            breach_start = None
            elapsed      = 0.0

        # ── Staged overlay ───────────────────────────────────────────
        if status == "NO_FACE":
            banner(frame, "No face detected", YELLOW)
            border(frame, YELLOW)

        elif status == "VERIFIED":
            banner(frame, f"VERIFIED  (d={cached_distance:.3f})", GREEN)
            border(frame, GREEN)

        else:  # MISMATCH — staged escalation
            if elapsed < YELLOW_END:
                tinted_overlay(frame, YELLOW, 0.07)
                border(frame, YELLOW)
                banner(frame, "Verifying identity...", YELLOW)

            elif elapsed < ORANGE_END:
                tinted_overlay(frame, ORANGE, 0.09)
                border(frame, ORANGE)
                banner(frame, "Identity mismatch — stay in frame", ORANGE)
                cv2.putText(frame, f"({ORANGE_END - elapsed:.1f}s to flag)",
                            (15, h - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.6, ORANGE, 1)

            else:
                tinted_overlay(frame, RED, 0.11)
                border(frame, RED)
                banner(frame, "WRONG CANDIDATE — FLAGGED", RED)
                cv2.putText(frame, f"Mismatch: {elapsed:.1f}s",
                            (15, h - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.8, RED, 2)

        # ── Threshold label in corner ────────────────────────────────
        cv2.putText(frame, f"thresh={MATCH_THRESHOLD}", (w - 160, h - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, WHITE, 1)

        # ── Write shared state ───────────────────────────────────────
        write_state(
            verified       = (status == "VERIFIED"),
            status         = status,
            breach_elapsed = elapsed,
        )

        cv2.imshow("Face Verifier", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()
    # Final state: clean shutdown
    write_state(verified=False, status="OFFLINE", breach_elapsed=0.0)
    print("[face_verifier] Shutdown complete.")


# ── ENTRY POINT ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Candidate Face Verifier")
    parser.add_argument(
        "--refs", default=REFERENCE_DIR,
        help=f"Path to folder containing 3-4 reference photos (default: {REFERENCE_DIR})"
    )
    args = parser.parse_args()
    main(args.refs)