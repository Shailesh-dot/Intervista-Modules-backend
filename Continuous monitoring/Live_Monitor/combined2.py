"""
Combined: Device Detection (YOLOv8n) + Gaze Tracking (MediaPipe)
- LENIENT face detection: no-face only logs a soft warning, no red flash
- STRICT gaze: center band 0.35-0.65
- TWO INDEPENDENT thresholds: face and gaze
- Staged breach warnings:
    0s - 1.5s  → YELLOW screen + "Look at the screen straight"
    1.5s - 3.5s → ORANGE screen + "About to be flagged"
    3.5s+       → RED screen + full warning (distracted timer)
- If breach is corrected before 3.5s, timer resets silently — no alarm at all
"""
import cv2
import numpy as np
import mediapipe as mp
from collections import deque
from ultralytics import YOLO
import time

# -- Models ------------------------------------------------------------
yolo = YOLO("yolov8n.pt")
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(
    max_num_faces=1, refine_landmarks=True,
    min_detection_confidence=0.7, min_tracking_confidence=0.7)

# -- Constants ---------------------------------------------------------
TARGET = {63: "Laptop", 67: "Phone", 76: "Tablet"}
LEFT_IRIS         = [474, 475, 476, 477]
RIGHT_IRIS        = [469, 470, 471, 472]
LEFT_EYE_CORNERS  = [33, 133]
RIGHT_EYE_CORNERS = [362, 263]

# -- FACE detection thresholds (independent) ---------------------------
FACE_LEFT_THRESH  = 0.25
FACE_RIGHT_THRESH = 0.75

# -- GAZE / EYE tracking thresholds (independent) ----------------------
GAZE_LEFT_THRESH  = 0.40
GAZE_RIGHT_THRESH = 0.60

# -- Staged breach timing ----------------------------------------------
BREACH_GRACE_PERIOD  = 3   # seconds before full red alert triggers
YELLOW_STAGE_END     = 1   # 0 - 1.5s  → yellow
ORANGE_STAGE_END     = 2   # 1.5 - 3.5s → orange
# beyond ORANGE_STAGE_END    → red

GREEN  = (0, 220, 0)
RED    = (0, 0, 220)
YELLOW = (0, 220, 255)
ORANGE = (0, 140, 255)
CYAN   = (255, 220, 0)
WHITE  = (255, 255, 255)

# -- Smoothing + frame-skip state --------------------------------------
gaze_buffer  = deque(maxlen=7)
frame_count  = 0
YOLO_EVERY   = 3
cached_boxes = []

# -- Breach timer state ------------------------------------------------
breach_start_time = None   # when the current continuous breach started
alert_triggered   = False  # True once the 3.5s grace period has expired


def iris_center(lm, ids, w, h):
    pts = [(int(lm[i].x * w), int(lm[i].y * h)) for i in ids]
    return int(np.mean([p[0] for p in pts])), int(np.mean([p[1] for p in pts]))


def eye_ratio(cx, corners, lm, w, h):
    lx = int(lm[corners[0]].x * w)
    rx = int(lm[corners[1]].x * w)
    return 0.5 if rx == lx else (cx - lx) / (rx - lx)


def face_position_ratio(lm):
    return lm[1].x  # nose tip, already normalized 0-1


def face_status(face_ratio):
    """Uses FACE thresholds only."""
    if face_ratio < FACE_LEFT_THRESH:
        return "FACE_LEFT",  RED,    "WARNING: Face turned LEFT"
    if face_ratio > FACE_RIGHT_THRESH:
        return "FACE_RIGHT", RED,    "WARNING: Face turned RIGHT"
    return "FACE_CENTER", GREEN, "Face Centered"


def gaze_status(avg):
    """Uses GAZE thresholds only."""
    if avg < GAZE_LEFT_THRESH:  return "LEFT",  RED,   "WARNING: Looking LEFT"
    if avg > GAZE_RIGHT_THRESH: return "RIGHT", RED,   "WARNING: Looking RIGHT"
    return "CENTER", GREEN, "STRAIGHT"


cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
print("Combined Detector -- Press Q to quit")
print(f"  Face thresholds  -> LEFT: {FACE_LEFT_THRESH} | RIGHT: {FACE_RIGHT_THRESH}")
print(f"  Gaze thresholds  -> LEFT: {GAZE_LEFT_THRESH} | RIGHT: {GAZE_RIGHT_THRESH}")
print(f"  Stage 1 (Yellow) -> 0s to {YELLOW_STAGE_END}s  : Look at the screen straight")
print(f"  Stage 2 (Orange) -> {YELLOW_STAGE_END}s to {ORANGE_STAGE_END}s : About to be flagged")
print(f"  Stage 3 (Red)    -> {ORANGE_STAGE_END}s+        : Full warning triggered")

while True:
    ret, frame = cap.read()
    if not ret:
        break

    frame = cv2.flip(frame, 1)
    h, w  = frame.shape[:2]
    frame_count += 1

    # -- YOLO every Nth frame ------------------------------------------
    if frame_count % YOLO_EVERY == 0:
        cached_boxes = []
        for box in yolo(frame, verbose=False, imgsz=320)[0].boxes:
            cls = int(box.cls)
            if cls not in TARGET:
                continue
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            cached_boxes.append((x1, y1, x2, y2, TARGET[cls], float(box.conf)))

    for (x1, y1, x2, y2, name, conf) in cached_boxes:
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(frame, f"{name} {conf:.2f}", (x1, y1 - 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

    # -- Gaze + Face every frame ---------------------------------------
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    res = face_mesh.process(rgb)
    cv2.rectangle(frame, (0, 0), (w, 55), (20, 20, 20), -1)

    breaching     = False
    gaze_dir      = "CENTER"
    face_dir      = "FACE_CENTER"
    gaze_msg      = "STRAIGHT"
    face_msg      = "Face Centered"
    gaze_color    = GREEN
    face_color    = GREEN
    smoothed_gaze = 0.5
    face_ratio    = 0.5

    if res.multi_face_landmarks:
        lm = res.multi_face_landmarks[0].landmark

        # -- Gaze (iris ratio) ----------------------------------------
        lcx, lcy = iris_center(lm, LEFT_IRIS,  w, h)
        rcx, rcy = iris_center(lm, RIGHT_IRIS, w, h)
        lr = eye_ratio(lcx, LEFT_EYE_CORNERS,  lm, w, h)
        rr = eye_ratio(rcx, RIGHT_EYE_CORNERS, lm, w, h)
        gaze_buffer.append((lr + rr) / 2)
        smoothed_gaze = float(np.mean(gaze_buffer))
        gaze_dir, gaze_color, gaze_msg = gaze_status(smoothed_gaze)

        # -- Face position --------------------------------------------
        face_ratio = face_position_ratio(lm)
        face_dir, face_color, face_msg = face_status(face_ratio)

        # -- Draw iris dots -------------------------------------------
        cv2.circle(frame, (lcx, lcy), 6, CYAN, -1)
        cv2.circle(frame, (rcx, rcy), 6, CYAN, -1)

        breaching = (gaze_dir != "CENTER") or (face_dir != "FACE_CENTER")

        # -- Ratio bars -----------------------------------------------
        bx, by, bw_bar = w - 170, 8, 150

        # Gaze bar
        fill = int(np.clip(smoothed_gaze, 0, 1) * bw_bar)
        cv2.rectangle(frame, (bx, by), (bx + bw_bar, by + 16), (60, 60, 60), -1)
        cv2.rectangle(frame, (bx, by), (bx + fill, by + 16),
                      GREEN if gaze_dir == "CENTER" else YELLOW, -1)
        cv2.putText(frame, f"G:{smoothed_gaze:.2f}", (bx - 52, by + 13),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, WHITE, 1)
        cv2.line(frame, (bx + int(GAZE_LEFT_THRESH  * bw_bar), by),
                        (bx + int(GAZE_LEFT_THRESH  * bw_bar), by + 16), (255, 255, 0), 2)
        cv2.line(frame, (bx + int(GAZE_RIGHT_THRESH * bw_bar), by),
                        (bx + int(GAZE_RIGHT_THRESH * bw_bar), by + 16), (255, 255, 0), 2)

        # Face bar
        fy = by + 24
        face_fill = int(np.clip(face_ratio, 0, 1) * bw_bar)
        cv2.rectangle(frame, (bx, fy), (bx + bw_bar, fy + 16), (60, 60, 60), -1)
        cv2.rectangle(frame, (bx, fy), (bx + face_fill, fy + 16),
                      GREEN if face_dir == "FACE_CENTER" else YELLOW, -1)
        cv2.putText(frame, f"F:{face_ratio:.2f}", (bx - 52, fy + 13),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, WHITE, 1)
        cv2.line(frame, (bx + int(FACE_LEFT_THRESH  * bw_bar), fy),
                        (bx + int(FACE_LEFT_THRESH  * bw_bar), fy + 16), (200, 200, 0), 2)
        cv2.line(frame, (bx + int(FACE_RIGHT_THRESH * bw_bar), fy),
                        (bx + int(FACE_RIGHT_THRESH * bw_bar), fy + 16), (200, 200, 0), 2)

    else:
        # LENIENT: no face — soft log, no alarm
        gaze_buffer.clear()
        cv2.putText(frame, "No face detected", (15, 38),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, YELLOW, 2)

    # -- Breach timer + staged overlay logic ---------------------------
    now = time.time()

    if breaching:
        if breach_start_time is None:
            breach_start_time = now
            alert_triggered   = False

        elapsed = now - breach_start_time

        if elapsed < YELLOW_STAGE_END:
            # ── STAGE 1: Yellow ───────────────────────────────────
            ov = frame.copy()
            cv2.rectangle(ov, (0, 0), (w, h), YELLOW, -1)
            cv2.addWeighted(ov, 0.07, frame, 0.93, 0, frame)
            cv2.rectangle(frame, (0, 0), (w - 1, h - 1), YELLOW, 3)
            cv2.putText(frame, "Look at the screen straight", (15, 38),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, YELLOW, 2)

        elif elapsed < ORANGE_STAGE_END:
            # ── STAGE 2: Orange ───────────────────────────────────
            ov = frame.copy()
            cv2.rectangle(ov, (0, 0), (w, h), ORANGE, -1)
            cv2.addWeighted(ov, 0.07, frame, 0.93, 0, frame)
            cv2.rectangle(frame, (0, 0), (w - 1, h - 1), ORANGE, 3)
            cv2.putText(frame, "About to be flagged", (15, 38),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, ORANGE, 2)
            cv2.putText(frame, f"({ORANGE_STAGE_END - elapsed:.1f}s)", (15, h - 15),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, ORANGE, 1)

        else:
            # ── STAGE 3: Red — full alert ─────────────────────────
            alert_triggered = True
            ov = frame.copy()
            cv2.rectangle(ov, (0, 0), (w, h), RED, -1)
            cv2.addWeighted(ov, 0.07, frame, 0.93, 0, frame)
            cv2.rectangle(frame, (0, 0), (w - 1, h - 1), RED, 3)

            primary_msg   = gaze_msg   if gaze_dir != "CENTER" else face_msg
            primary_color = gaze_color if gaze_dir != "CENTER" else face_color
            cv2.putText(frame, primary_msg, (15, 38),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, primary_color, 2)
            cv2.putText(frame, f"ERROR: Distracted {elapsed:.1f}s", (15, h - 15),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, RED, 2)

    else:
        # Not breaching — reset everything silently
        breach_start_time = None
        alert_triggered   = False

        if res.multi_face_landmarks:
            cv2.putText(frame, "STRAIGHT", (15, 38),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, GREEN, 2)

    cv2.imshow("Device + Gaze Detector", frame)
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()
face_mesh.close()