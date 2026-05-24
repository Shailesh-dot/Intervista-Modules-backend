import cv2
import numpy as np
import mediapipe as mp
import os

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from sqlalchemy.orm import Session
from app.database.db import get_db
from app.database.models import IdentityVerification

from app.face.model import get_face_embedding
from app.face.utils import cosine_similarity
from app.liveness.blink_detector import detect_blink
from app.liveness.gaze_detector import get_eye_direction
from app.liveness.screen_detector import detect_screen
from app.config import EMBED_STORAGE, PASSPORT_STORAGE, FACE_THRESHOLD
from app.utils.cloudinary_utils import upload_to_cloudinary

router = APIRouter(prefix="/liveness", tags=["Liveness"])

mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(
    static_image_mode=False,
    max_num_faces=1,
    refine_landmarks=True,
)

# In-memory session stores (keyed by unique_id)
_blink_counts: dict[str, int] = {}


def _decode_frame(raw: bytes) -> np.ndarray:
    arr = np.frombuffer(raw, np.uint8)
    frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if frame is None:
        raise ValueError("Could not decode image frame")
    return frame


@router.post("/check")
async def liveness_check(
    unique_id: str = Form(...),
    step: str = Form(...),
    frame: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Stateful liveness check endpoint.
    Steps (in order): BLINK → LEFT → RIGHT → CENTER
    """
    raw = await frame.read()

    try:
        img = _decode_frame(raw)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    h, w, _ = img.shape
    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    result = face_mesh.process(rgb)

    if not result.multi_face_landmarks:
        return {"status": "WAITING", "message": "No face detected — please centre your face"}

    landmarks = result.multi_face_landmarks[0].landmark

    # ----------------------------------------------------------------
    # BLINK detection
    # ----------------------------------------------------------------
    if step == "BLINK":
        count = _blink_counts.get(unique_id, 0)
        if detect_blink(landmarks):
            count += 1
            _blink_counts[unique_id] = count
        if count >= 2:
            _blink_counts.pop(unique_id, None)
            return {"status": "SUCCESS", "message": "Blink detected"}
        return {"status": "WAITING", "message": f"Please blink your eyes ({count}/2 detected)"}

    # ----------------------------------------------------------------
    # LOOK LEFT
    # ----------------------------------------------------------------
    if step == "LEFT":
        direction = get_eye_direction(landmarks)
        if direction == "LEFT":
            return {"status": "SUCCESS", "message": "Looking left confirmed"}
        return {"status": "WAITING", "message": "Please look to your LEFT"}

    # ----------------------------------------------------------------
    # LOOK RIGHT
    # ----------------------------------------------------------------
    if step == "RIGHT":
        direction = get_eye_direction(landmarks)
        if direction == "RIGHT":
            return {"status": "SUCCESS", "message": "Looking right confirmed"}
        return {"status": "WAITING", "message": "Please look to your RIGHT"}

    # ----------------------------------------------------------------
    # CENTER — final face match + anti-spoof + store passport photo
    # ----------------------------------------------------------------
    if step == "CENTER":
        direction = get_eye_direction(landmarks)
        if direction != "CENTER":
            return {"status": "WAITING", "message": "Please look straight at the camera"}

        # Anti-spoof - Use non-aggressive mode to avoid false positives
        if detect_screen(img, aggressive=False):
            return {"status": "FAILED", "message": "Screen/mobile detected. Use your real face."}

        # Locate stored embedding
        embed_path = f"{EMBED_STORAGE}/{unique_id}.npy"
        if not os.path.exists(embed_path):
            return {"status": "FAILED", "message": "No face embedding found. Please restart verification."}

        stored_emb = np.load(embed_path)

        # Use full image for embedding to provide maximum context to the model
        current_emb = get_face_embedding(img)
        if current_emb is None:
            # Fallback to cropped if full frame fails (unlikely)
            xs = [lm.x for lm in landmarks]
            ys = [lm.y for lm in landmarks]
            x1, y1 = int(min(xs) * w), int(min(ys) * h)
            x2, y2 = int(max(xs) * w), int(max(ys) * h)
            face_crop = img[y1:y2, x1:x2]
            if face_crop.size > 0:
                face_crop = cv2.resize(face_crop, (640, 640))
                current_emb = get_face_embedding(face_crop)
            
        if current_emb is None:
            return {"status": "WAITING", "message": "Face not clear. Please move closer to the camera."}

        similarity = cosine_similarity(stored_emb, current_emb)
        if float(similarity) < FACE_THRESHOLD:
            return {
                "status": "FAILED",
                "message": f"Face did not match (similarity {similarity:.2f}). Verification failed.",
            }

        # Save result to Cloudinary
        os.makedirs(PASSPORT_STORAGE, exist_ok=True)
        temp_path = f"{PASSPORT_STORAGE}/{unique_id}_temp.jpg"
        cv2.imwrite(temp_path, img)
        
        cloudinary_url = upload_to_cloudinary(temp_path, folder="passports")
        if os.path.exists(temp_path):
            os.remove(temp_path)

        if cloudinary_url:
            record = db.query(IdentityVerification).filter(IdentityVerification.unique_id == unique_id).first()
            if record:
                record.passport_photo_url = cloudinary_url
                db.commit()

        return {
            "status": "SUCCESS",
            "message": "Liveness verification passed!",
            "photo_url": cloudinary_url,
        }

    return {"status": "FAILED", "message": f"Unknown liveness step: {step}"}
