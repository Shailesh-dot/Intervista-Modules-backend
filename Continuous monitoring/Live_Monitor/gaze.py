import cv2
import mediapipe as mp
import numpy as np

# ── MediaPipe setup ──────────────────────────────────────────
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(
    max_num_faces=1,
    refine_landmarks=True,   # enables iris landmarks
    min_detection_confidence=0.7,
    min_tracking_confidence=0.7,
)

# ── Iris landmark indices (MediaPipe 478-point model) ─────────
# Left eye iris: 474-477, Right eye iris: 469-472
LEFT_IRIS  = [474, 475, 476, 477]
RIGHT_IRIS = [469, 470, 471, 472]

# Eye corner landmarks for ratio reference
LEFT_EYE_CORNERS  = [33, 133]   # inner, outer
RIGHT_EYE_CORNERS = [362, 263]

# ── Thresholds ────────────────────────────────────────────────
LEFT_THRESH  = 0.38   # iris ratio below this → looking left
RIGHT_THRESH = 0.62   # iris ratio above this → looking right
STRAIGHT_MARGIN = 0.08  # vertical dead-zone (up/down tolerance)

# ── Colors ───────────────────────────────────────────────────
GREEN  = (0, 220, 0)
YELLOW = (0, 220, 255)
RED    = (0, 0, 220)
WHITE  = (255, 255, 255)
CYAN   = (255, 220, 0)


def iris_center(landmarks, indices, w, h):
    pts = [(int(landmarks[i].x * w), int(landmarks[i].y * h)) for i in indices]
    cx = int(np.mean([p[0] for p in pts]))
    cy = int(np.mean([p[1] for p in pts]))
    return cx, cy, pts


def eye_ratio(iris_cx, corner_ids, landmarks, w, h):
    """Horizontal ratio: 0.0 = far left, 1.0 = far right"""
    lx = int(landmarks[corner_ids[0]].x * w)
    rx = int(landmarks[corner_ids[1]].x * w)
    if rx == lx:
        return 0.5
    return (iris_cx - lx) / (rx - lx)


def gaze_status(left_ratio, right_ratio):
    avg = (left_ratio + right_ratio) / 2
    if avg < LEFT_THRESH:
        return "LEFT", RED, "⚠ Looking LEFT"
    elif avg > RIGHT_THRESH:
        return "RIGHT", RED, "⚠ Looking RIGHT"
    else:
        return "CENTER", GREEN, "✓ Looking STRAIGHT"


def draw_hud(frame, direction, color, message, left_r, right_r):
    h, w = frame.shape[:2]

    # Status bar background
    cv2.rectangle(frame, (0, 0), (w, 60), (20, 20, 20), -1)

    # Main message
    cv2.putText(frame, message, (15, 42),
                cv2.FONT_HERSHEY_SIMPLEX, 1.2, color, 2)

    # Gaze ratio meters
    bar_w = 200
    bar_x, bar_y = w - 220, 10

    for label, ratio in [("L", left_r), ("R", right_r)]:
        fill = int(ratio * bar_w)
        fill = max(0, min(fill, bar_w))
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + 18), (60, 60, 60), -1)
        bar_color = GREEN if LEFT_THRESH < ratio < RIGHT_THRESH else RED
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + fill, bar_y + 18), bar_color, -1)
        cv2.putText(frame, f"{label}:{ratio:.2f}", (bar_x - 55, bar_y + 14),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, WHITE, 1)
        bar_y += 26

    # Warning flash overlay
    if direction != "CENTER":
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, h), RED, -1)
        cv2.addWeighted(overlay, 0.08, frame, 0.92, 0, frame)
        cv2.rectangle(frame, (0, 0), (w - 1, h - 1), RED, 3)


cap = cv2.VideoCapture(0)
if not cap.isOpened():
    raise RuntimeError("Cannot open camera")

print("Gaze Detector running — Press Q to quit")

while True:
    ret, frame = cap.read()
    if not ret:
        break

    frame = cv2.flip(frame, 1)
    h, w = frame.shape[:2]
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = face_mesh.process(rgb)

    if results.multi_face_landmarks:
        lm = results.multi_face_landmarks[0].landmark

        # Iris centers
        lcx, lcy, l_pts = iris_center(lm, LEFT_IRIS,  w, h)
        rcx, rcy, r_pts = iris_center(lm, RIGHT_IRIS, w, h)

        # Gaze ratios
        left_r  = eye_ratio(lcx, LEFT_EYE_CORNERS,  lm, w, h)
        right_r = eye_ratio(rcx, RIGHT_EYE_CORNERS, lm, w, h)

        direction, color, message = gaze_status(left_r, right_r)

        # Draw iris circles
        cv2.circle(frame, (lcx, lcy), 6, CYAN, -1)
        cv2.circle(frame, (rcx, rcy), 6, CYAN, -1)
        for p in l_pts + r_pts:
            cv2.circle(frame, p, 2, YELLOW, -1)

        draw_hud(frame, direction, color, message, left_r, right_r)

    else:
        cv2.rectangle(frame, (0, 0), (w, 60), (20, 20, 20), -1)
        cv2.putText(frame, "No face detected", (15, 42),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, YELLOW, 2)

    cv2.imshow("Gaze Detector", frame)
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()
face_mesh.close()