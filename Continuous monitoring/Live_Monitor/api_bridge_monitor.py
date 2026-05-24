"""
api_bridge_monitor.py
---------------------
FastAPI bridge for the Live_Monitor module.
Exposes gaze tracking (MediaPipe) + device detection (YOLOv8) via HTTP.

Runs on Port 8005.
Does NOT modify any existing file in this folder.

Endpoints:
  GET  /status      → gaze + device violation JSON
  GET  /video_feed  → MJPEG live stream with overlays
  POST /start       → starts the background monitoring loop
  POST /stop        → stops the monitoring loop

Usage:
  pip install fastapi uvicorn python-multipart
  python api_bridge_monitor.py
"""

import cv2
import time
import threading
import numpy as np
from collections import deque

import mediapipe as mp
from ultralytics import YOLO

import uvicorn
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

import torch
from contextlib import asynccontextmanager

# ─── Torch 2.6+ Fix ────────────────────────────────────────────────────────────
# Allow-list Ultralytics classes for safe unpickling
try:
    from ultralytics.nn.tasks import DetectionModel
    if hasattr(torch.serialization, 'add_safe_globals'):
        torch.serialization.add_safe_globals([DetectionModel])
except Exception:
    pass

# ─── FastAPI App ───────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    load_models()
    yield
    # Shutdown logic (optional)
    global _running
    _running = False

app = FastAPI(
    title="Live Monitor Bridge API — Gaze + Device Detection",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Models (loaded once at startup) ──────────────────────────────────────────
yolo_model = None
face_mesh  = None

def load_models():
    global yolo_model, face_mesh
    print("[MONITOR-BRIDGE] Loading YOLOv8n model...")
    
    # ─── Torch 2.6+ Compatibility Fix ───
    # Temporarily force weights_only=False for the YOLO loader
    import torch
    original_load = torch.load
    def patched_load(*args, **kwargs):
        kwargs['weights_only'] = False
        return original_load(*args, **kwargs)
    
    torch.load = patched_load
    try:
        yolo_model = YOLO("yolov8n.pt")
    finally:
        torch.load = original_load
        
    print("[MONITOR-BRIDGE] Loading MediaPipe FaceMesh...")
    mp_face_mesh = mp.solutions.face_mesh
    face_mesh = mp_face_mesh.FaceMesh(
        max_num_faces=1,
        refine_landmarks=True,
        min_detection_confidence=0.7,
        min_tracking_confidence=0.7,
    )
    print("[MONITOR-BRIDGE] Models ready.")

# ─── YOLO Target Classes ───────────────────────────────────────────────────────
TARGET_CLASSES = {63: "Laptop", 67: "Phone", 76: "Tablet"}

# ─── Gaze Thresholds ──────────────────────────────────────────────────────────
GAZE_LEFT_THRESH  = 0.38
GAZE_RIGHT_THRESH = 0.62

# ─── MediaPipe Landmark Indices ───────────────────────────────────────────────
LEFT_IRIS         = [474, 475, 476, 477]
RIGHT_IRIS        = [469, 470, 471, 472]
LEFT_EYE_CORNERS  = [33, 133]
RIGHT_EYE_CORNERS = [362, 263]

# ─── Breach Staging Timings (seconds) ─────────────────────────────────────────
YELLOW_STAGE_END = 1.0   # 0–1s   → warn
ORANGE_STAGE_END = 2.5   # 1–2.5s → about to flag
# beyond 2.5s → fully flagged

# ─── Shared State (thread-safe) ───────────────────────────────────────────────
_lock = threading.Lock()

_state = {
    # Gaze
    "gaze_direction":  "CENTER",        # CENTER | LEFT | RIGHT
    "gaze_ratio":       0.5,
    "gaze_breach_sec":  0.0,
    "gaze_flagged":     False,
    "gaze_message":    "Initialising...",

    # Device
    "device_detected":  False,
    "device_names":     [],             # e.g. ["Phone", "Laptop"]

    # Overall
    "violations":       0,
    "online":           False,
}

_latest_frame = None
_running      = False
_cap_thread   = None

# ─── Helpers ──────────────────────────────────────────────────────────────────

def _iris_center(lm, ids, w, h):
    pts = [(int(lm[i].x * w), int(lm[i].y * h)) for i in ids]
    return int(np.mean([p[0] for p in pts])), int(np.mean([p[1] for p in pts]))


def _eye_ratio(cx, corners, lm, w, h):
    lx = int(lm[corners[0]].x * w)
    rx = int(lm[corners[1]].x * w)
    if rx == lx:
        return 0.5
    return (cx - lx) / (rx - lx)


def _draw_status_bar(frame, text, color):
    h, w = frame.shape[:2]
    cv2.rectangle(frame, (0, 0), (w, 50), (15, 15, 15), -1)
    cv2.putText(frame, text, (12, 36), cv2.FONT_HERSHEY_SIMPLEX, 0.85, color, 2)


def _tint(frame, color, alpha=0.08):
    overlay = frame.copy()
    h, w = frame.shape[:2]
    cv2.rectangle(overlay, (0, 0), (w, h), color, -1)
    cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)
    cv2.rectangle(frame, (0, 0), (w - 1, h - 1), color, 3)


# ─── Camera source: read from Port 8004's MJPEG stream ──────────────────────
# This avoids camera hardware conflict — Port 8004 owns the physical camera;
# Port 8005 reads the already-captured frames from its HTTP stream.
FACE_STREAM_URL = "http://localhost:8004/video_feed"

# ─── Background Monitoring Loop ───────────────────────────────────────────────

def _monitor_loop():
    global _latest_frame, _running, _state

    print("[MONITOR-BRIDGE] Connecting to face stream at Port 8004...")
    cap = cv2.VideoCapture(FACE_STREAM_URL)

    # Retry up to 4 seconds waiting for Port 8004 to be ready
    retries = 0
    while not cap.isOpened() and retries < 8 and _running:
        print(f"[MONITOR-BRIDGE] Waiting for Port 8004 stream... ({retries+1}/8)")
        time.sleep(0.5)
        cap = cv2.VideoCapture(FACE_STREAM_URL)
        retries += 1

    if not cap.isOpened():
        print("[MONITOR-BRIDGE] ERROR: Could not connect to Port 8004 stream. Is api_bridge.py running?")
        _running = False
        return

    print("[MONITOR-BRIDGE] Connected to Port 8004 stream. Gaze+Device monitoring started.")

    gaze_buffer      = deque(maxlen=5)   # smaller buffer = faster reaction
    frame_count      = 0
    YOLO_EVERY       = 5          # run YOLO every 5 frames (~3/sec at 15fps)
    GAZE_EVERY       = 2          # run MediaPipe gaze every 2nd frame
    cached_boxes     = []
    cached_gaze_dir  = "CENTER"
    cached_gaze_ratio = 0.5
    cached_gaze_msg  = "Looking STRAIGHT"
    breach_start     = None
    total_violations = 0

    # ── Violation debounce flags (prevent per-frame overcounting) ──────────────
    device_was_active  = False   # True while a device is continuously visible
    gaze_was_flagged   = False   # True while gaze is continuously in red stage

    GREEN  = (0, 210, 0)
    RED    = (30, 30, 220)
    YELLOW = (0, 215, 255)
    ORANGE = (0, 130, 255)
    CYAN   = (255, 210, 0)

    while _running:
        ret, frame = cap.read()
        if not ret:
            # Stream dropped — try to reconnect
            print("[MONITOR-BRIDGE] Stream lost, reconnecting...")
            cap.release()
            time.sleep(1.0)
            cap = cv2.VideoCapture(FACE_STREAM_URL)
            continue

        # Port 8004 stream is already flipped; don't flip again
        h, w  = frame.shape[:2]
        frame_count += 1

        # ── YOLO Device Detection (every 5th frame) ───────────
        if frame_count % YOLO_EVERY == 0:
            cached_boxes = []
            # Use full 640 resolution so small objects at the edges are not lost
            results = yolo_model(frame, verbose=False, imgsz=640, conf=0.25)
            for box in results[0].boxes:
                cls = int(box.cls)
                if cls not in TARGET_CLASSES:
                    continue
                x1, y1, x2, y2 = [int(v) for v in box.xyxy[0]]
                cached_boxes.append((
                    x1, y1, x2, y2,
                    TARGET_CLASSES[cls], float(box.conf)
                ))

        device_detected = len(cached_boxes) > 0
        device_names    = list({b[4] for b in cached_boxes})

        # Draw device boxes on frame
        for (x1, y1, x2, y2, name, conf) in cached_boxes:
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(frame, f"{name} {conf:.2f}", (x1, max(y1 - 8, 12)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        # ── Gaze Tracking (every 2nd frame — halves MediaPipe CPU load) ─
        if frame_count % GAZE_EVERY == 0:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            res = face_mesh.process(rgb)
        else:
            res = None  # use cached result from last gaze frame

        gaze_dir   = cached_gaze_dir
        gaze_ratio = cached_gaze_ratio
        gaze_msg   = cached_gaze_msg
        breaching  = device_detected  # device = immediate breach

        if res is not None and res.multi_face_landmarks:
            lm = res.multi_face_landmarks[0].landmark

            lcx, lcy = _iris_center(lm, LEFT_IRIS,  w, h)
            rcx, rcy = _iris_center(lm, RIGHT_IRIS, w, h)

            lr = _eye_ratio(lcx, LEFT_EYE_CORNERS,  lm, w, h)
            rr = _eye_ratio(rcx, RIGHT_EYE_CORNERS, lm, w, h)

            gaze_buffer.append((lr + rr) / 2)
            gaze_ratio = float(np.mean(gaze_buffer))

            if gaze_ratio < GAZE_LEFT_THRESH:
                gaze_dir  = "LEFT"
                gaze_msg  = "Looking LEFT"
                breaching = True
            elif gaze_ratio > GAZE_RIGHT_THRESH:
                gaze_dir  = "RIGHT"
                gaze_msg  = "Looking RIGHT"
                breaching = True
            else:
                gaze_dir = "CENTER"
                gaze_msg = "Looking STRAIGHT"

            # Cache for skipped frames
            cached_gaze_dir   = gaze_dir
            cached_gaze_ratio = gaze_ratio
            cached_gaze_msg   = gaze_msg

            # Draw iris dots
            cv2.circle(frame, (lcx, lcy), 5, CYAN, -1)
            cv2.circle(frame, (rcx, rcy), 5, CYAN, -1)

        elif res is not None:
            gaze_buffer.clear()
            cached_gaze_msg = "No face detected"
            gaze_msg = "No face detected"

        # ── Breach Timer + Staged Overlays ────────────────────────────
        now         = time.time()
        breach_secs = 0.0
        gaze_flagged = False

        if breaching:
            if breach_start is None:
                breach_start = now
            breach_secs = now - breach_start

            if device_detected:
                # Device found — red immediately
                _tint(frame, RED, 0.10)
                _draw_status_bar(frame, f"ALERT: {', '.join(device_names)} detected!", RED)
                gaze_flagged = True
                # ── Count only ONCE per new device appearance (debounce) ─────
                if not device_was_active:
                    total_violations += 1
                    device_was_active = True

            elif breach_secs < YELLOW_STAGE_END:
                _tint(frame, YELLOW, 0.06)
                _draw_status_bar(frame, f"WARNING: {gaze_msg}", YELLOW)
                device_was_active = False

            elif breach_secs < ORANGE_STAGE_END:
                _tint(frame, ORANGE, 0.08)
                _draw_status_bar(frame, f"About to be flagged — {gaze_msg}", ORANGE)
                device_was_active = False

            else:
                _tint(frame, RED, 0.10)
                _draw_status_bar(frame, f"FLAGGED: {gaze_msg} ({breach_secs:.1f}s)", RED)
                gaze_flagged = True
                # ── Count only ONCE per new gaze-red breach (debounce) ────────
                if not gaze_was_flagged:
                    total_violations += 1
                    gaze_was_flagged = True
                device_was_active = False

        else:
            breach_start     = None
            device_was_active = False
            gaze_was_flagged  = False
            _draw_status_bar(frame, gaze_msg, GREEN)

        # ── Update Shared State ───────────────────────────────────────
        with _lock:
            _state["gaze_direction"]  = gaze_dir
            _state["gaze_ratio"]      = round(gaze_ratio, 3)
            _state["gaze_breach_sec"] = round(breach_secs, 2)
            _state["gaze_flagged"]    = gaze_flagged
            _state["gaze_message"]    = gaze_msg
            _state["device_detected"] = device_detected
            _state["device_names"]    = device_names
            _state["violations"]      = total_violations
            _state["online"]          = True
            _latest_frame             = frame.copy()

        # No sleep — the MJPEG stream read from Port 8004 naturally throttles
        # us to Port 8004's own output rate. Adding sleep only adds extra lag.

    cap.release()
    with _lock:
        _state["online"] = False
    print("[MONITOR-BRIDGE] Camera released. Monitoring stopped.")


# ─── Frame Generator for MJPEG Stream ─────────────────────────────────────────

def _generate_frames():
    global _latest_frame
    while True:
        with _lock:
            frame = _latest_frame.copy() if _latest_frame is not None else None

        if frame is not None:
            ret, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 52])
            if ret:
                yield (
                    b'--frame\r\n'
                    b'Content-Type: image/jpeg\r\n\r\n'
                    + buf.tobytes()
                    + b'\r\n'
                )
        else:
            time.sleep(0.05)


# ─── API Endpoints ─────────────────────────────────────────────────────────────


@app.post("/start")
def start_monitoring():
    global _running, _cap_thread
    if _running:
        return {"status": "already_running"}
    _running    = True
    _cap_thread = threading.Thread(target=_monitor_loop, daemon=True, name="MonitorLoop")
    _cap_thread.start()
    return {"status": "started"}


@app.post("/stop")
def stop_monitoring():
    global _running
    _running = False
    return {"status": "stopped"}


@app.get("/status")
def get_status():
    with _lock:
        return dict(_state)


@app.get("/video_feed")
def video_feed():
    return StreamingResponse(
        _generate_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


# ─── Entry Point ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8005)
