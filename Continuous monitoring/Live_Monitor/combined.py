"""
Combined: Device Detection (YOLOv8n) + Gaze Tracking (MediaPipe)
- LENIENT face detection: no-face only logs a soft warning, no red flash
- STRICT gaze: center band is 0.47–0.53 (was 0.44–0.58), any deviation triggers alert
"""
import cv2
import numpy as np
import mediapipe as mp
from collections import deque
from ultralytics import YOLO

# ── Models ────────────────────────────────────────────────────
yolo = YOLO("yolov8n.pt")
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(
    max_num_faces=1, refine_landmarks=True,
    min_detection_confidence=0.7, min_tracking_confidence=0.7)

# ── Constants ─────────────────────────────────────────────────
TARGET = {63: "Laptop", 67: "Phone", 76: "Tablet"}
LEFT_IRIS         = [474, 475, 476, 477]
RIGHT_IRIS        = [469, 470, 471, 472]
LEFT_EYE_CORNERS  = [33, 133]
RIGHT_EYE_CORNERS = [362, 263]

# ── STRICT gaze thresholds ─────────────────────────────────────
# Center band: 0.47–0.53 (very tight — any meaningful eye movement triggers warning)
LEFT_THRESH  = 0.35
RIGHT_THRESH = 0.65

GREEN  = (0, 220, 0)
RED    = (0, 0, 220)
YELLOW = (0, 220, 255)
CYAN   = (255, 220, 0)

# ── Smoothing + frame-skip state ──────────────────────────────
gaze_buffer  = deque(maxlen=9)
frame_count  = 0
YOLO_EVERY   = 3
cached_boxes = []


def iris_center(lm, ids, w, h):
    pts = [(int(lm[i].x * w), int(lm[i].y * h)) for i in ids]
    return int(np.mean([p[0] for p in pts])), int(np.mean([p[1] for p in pts]))


def eye_ratio(cx, corners, lm, w, h):
    lx = int(lm[corners[0]].x * w)
    rx = int(lm[corners[1]].x * w)
    return 0.5 if rx == lx else (cx - lx) / (rx - lx)


def gaze_status(avg):
    if avg < LEFT_THRESH:  return "LEFT",  RED,   "WARNING: Looking LEFT"
    if avg > RIGHT_THRESH: return "RIGHT", RED,   "WARNING: Looking RIGHT"
    return "CENTER", GREEN, "STRAIGHT"


cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
print("Combined Detector — Press Q to quit")

while True:
    ret, frame = cap.read()
    if not ret:
        break

    frame = cv2.flip(frame, 1)
    h, w  = frame.shape[:2]
    frame_count += 1

    # ── YOLO every Nth frame ───────────────────────────────────
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

    # ── Gaze every frame ──────────────────────────────────────
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    res = face_mesh.process(rgb)
    cv2.rectangle(frame, (0, 0), (w, 55), (20, 20, 20), -1)

    if res.multi_face_landmarks:
        lm = res.multi_face_landmarks[0].landmark

        lcx, lcy = iris_center(lm, LEFT_IRIS,  w, h)
        rcx, rcy = iris_center(lm, RIGHT_IRIS, w, h)
        lr = eye_ratio(lcx, LEFT_EYE_CORNERS,  lm, w, h)
        rr = eye_ratio(rcx, RIGHT_EYE_CORNERS, lm, w, h)

        gaze_buffer.append((lr + rr) / 2)
        smoothed = float(np.mean(gaze_buffer))

        direction, color, msg = gaze_status(smoothed)

        cv2.circle(frame, (lcx, lcy), 6, CYAN, -1)
        cv2.circle(frame, (rcx, rcy), 6, CYAN, -1)
        cv2.putText(frame, msg, (15, 38), cv2.FONT_HERSHEY_SIMPLEX, 1.0, color, 2)

        # Ratio bar (top-right)
        bx, by, bw = w - 170, 8, 150
        fill = int(np.clip(smoothed, 0, 1) * bw)
        cv2.rectangle(frame, (bx, by), (bx + bw, by + 16), (60, 60, 60), -1)
        cv2.rectangle(frame, (bx, by), (bx + fill, by + 16),
                      GREEN if LEFT_THRESH < smoothed < RIGHT_THRESH else RED, -1)
        cv2.putText(frame, f"{smoothed:.2f}", (bx - 42, by + 13),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)

        left_mark  = bx + int(LEFT_THRESH  * bw)
        right_mark = bx + int(RIGHT_THRESH * bw)
        cv2.line(frame, (left_mark,  by), (left_mark,  by + 16), (255, 255, 0), 2)
        cv2.line(frame, (right_mark, by), (right_mark, by + 16), (255, 255, 0), 2)

        # ── STRICT: red flash on ANY off-center gaze ──────────
        if direction != "CENTER":
            ov = frame.copy()
            cv2.rectangle(ov, (0, 0), (w, h), RED, -1)
            cv2.addWeighted(ov, 0.07, frame, 0.93, 0, frame)
            cv2.rectangle(frame, (0, 0), (w - 1, h - 1), RED, 3)

    else:
        # ── LENIENT: no face = soft log only, no visual alarm ──
        gaze_buffer.clear()
        cv2.putText(frame, "No face detected", (15, 38),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, YELLOW, 2)
        # No red overlay, no border flash — just the yellow text

    cv2.imshow("Device + Gaze Detector", frame)
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()
face_mesh.close()