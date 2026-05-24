# Authorised Face Recognition System

Industry-grade, single-person face authorisation engine built on
`face_recognition` (dlib) and OpenCV.

---

## File Structure

```
face_auth/
├── face_engine.py       # Core engine (FaceAuthEngine, FaceAuthResult)
├── stream_verifier.py   # Threaded live-stream verifier
├── audit_logger.py      # Rotating JSON audit trail
├── config.py            # Centralised config + env-var overrides
├── main.py              # CLI entry point (image / batch / stream modes)
├── requirements.txt
├── reference_images/    # ← PUT authorised person's photos here
│   ├── person_front.jpg
│   ├── person_left.jpg
│   └── person_right.jpg
├── logs/                # Auto-created; audit JSONL files written here
└── tests/
    └── test_face_engine.py
```

---

## Installation

### 1. System dependencies

**Ubuntu / Debian**
```bash
sudo apt-get install -y cmake build-essential \
    libopenblas-dev liblapack-dev libx11-dev libgtk-3-dev python3-dev
```

**macOS**
```bash
brew install cmake
```

**Windows**
Install [CMake](https://cmake.org) and Visual Studio Build Tools, then proceed.

### 2. Python environment

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

---

## Reference Images

Place **1–10 clear photos of the ONE authorised person** in `reference_images/`.
- Photos should be well-lit, unobstructed, varied angles (front, slight left/right)
- Supported formats: `.jpg`, `.jpeg`, `.png`, `.bmp`, `.tiff`, `.webp`
- More reference images = more robust matching

```
reference_images/
├── alice_front.jpg
├── alice_left.jpg
└── alice_right.jpg
```

---

## Usage

### Verify a single image

```bash
python main.py image --input photo.jpg
```

### Batch verify a folder of images

```bash
python main.py batch --input-dir test_frames/
```

### Live stream (webcam)

```bash
python main.py stream --source 0          # default camera
python main.py stream --source 1          # second camera
python main.py stream --source "rtsp://user:pass@192.168.1.10/stream"
```

### Override reference directory or tolerance

```bash
python main.py --reference-dir /secure/refs --tolerance 0.45 image --input face.jpg
```

---

## Environment Variables

| Variable                   | Default            | Description                          |
|----------------------------|--------------------|--------------------------------------|
| `FACE_AUTH_REFERENCE_DIR`  | `reference_images` | Path to reference images folder      |
| `FACE_AUTH_TOLERANCE`      | `0.50`             | Match threshold (lower = stricter)   |
| `FACE_AUTH_MODEL`          | `hog`              | `hog` (CPU) or `cnn` (GPU)           |
| `FACE_AUTH_UPSAMPLE`       | `1`                | Upsampling passes during detection   |
| `FACE_AUTH_MIN_FACE_AREA`  | `0.005`            | Min face/frame area ratio            |
| `FACE_AUTH_CAMERA_SOURCE`  | `0`                | Camera index or RTSP URL             |
| `FACE_AUTH_STREAM_FPS`     | `5.0`              | Verification rate for stream mode    |
| `FACE_AUTH_LOG_DIR`        | `logs`             | Audit log output directory           |
| `FACE_AUTH_ACTOR_ID`       | `gate-1`           | Gate/door identifier in audit log    |
| `FACE_AUTH_LOG_LEVEL`      | `INFO`             | Python log level                     |

---

## Using as a Library

```python
from face_engine import FaceAuthEngine, AuthStatus
from audit_logger import AuditLogger
import cv2

engine = FaceAuthEngine(
    reference_dir="reference_images",
    tolerance=0.50,
    model="hog",
)

auditor = AuditLogger(log_dir="logs", actor_id="door-1")

# Verify a frame (BGR numpy array from OpenCV)
frame = cv2.imread("probe.jpg")
result = engine.verify_frame(frame)
auditor.log(result, source="probe.jpg")

if result.authorised:
    print("ACCESS GRANTED")
elif result.status == AuthStatus.MULTIPLE_FACES:
    print("ERROR: Multiple people in frame")
elif result.status == AuthStatus.UNAUTHORISED:
    print("ACCESS DENIED: Unknown person")
elif result.status == AuthStatus.NO_FACE:
    print("No face detected")

print(result.to_dict())
```

---

## AuthStatus Reference

| Status                | Meaning                                                  |
|-----------------------|----------------------------------------------------------|
| `AUTHORISED`          | Exactly one face, matches reference. Access granted.     |
| `NO_FACE`             | No face detected in the frame.                           |
| `MULTIPLE_FACES`      | More than one face detected. Access denied.              |
| `UNAUTHORISED`        | One face found but does NOT match the reference.         |
| `NO_REFERENCE`        | Reference folder is empty or has no valid face images.   |
| `REFERENCE_LOAD_ERROR`| Reference folder missing or images unreadable.           |

---

## Running Tests

```bash
pytest tests/ -v --tb=short
```

---

## Tuning Tolerance

| Scenario                  | Recommended `tolerance` |
|---------------------------|-------------------------|
| High-security gate        | 0.40 – 0.45             |
| Standard office access    | 0.50 (default)          |
| Loose / convenience check | 0.55 – 0.60             |

Lower tolerance reduces false accepts but may increase false rejects
(e.g., same person with glasses, different lighting).

---

## Audit Log Format

Each event appended to `logs/face_auth_audit.jsonl`:

```json
{"ts":"2024-01-15T10:23:01Z","actor_id":"gate-1","status":"AUTHORISED","authorised":true,"faces_detected":1,"confidence":0.8712,"latency_ms":43.2,"message":"Access granted. Authorised person verified.","source":"camera-0"}
{"ts":"2024-01-15T10:23:05Z","actor_id":"gate-1","status":"MULTIPLE_FACES","authorised":false,"faces_detected":2,"confidence":null,"latency_ms":51.1,"message":"Multiple faces detected (2). Only one person allowed in the frame.","source":"camera-0"}
```
