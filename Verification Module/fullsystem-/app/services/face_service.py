import cv2
import numpy as np
import os
import json

from app.face.model import get_face_embedding
from app.utils.cloudinary_utils import upload_to_cloudinary


AADHAAR_STORAGE = "app/storage/aadhaar"
PASSPORT_STORAGE = "app/storage/passport"
EMBED_STORAGE = "app/storage/embeddings"

THRESHOLD = 0.4


def verify_face(unique_id, masked_aadhaar, uploaded_photo):

    # -----------------------
    # Check user folder
    # -----------------------
    user_folder = f"{AADHAAR_STORAGE}/{unique_id}"

    if not os.path.exists(user_folder):
        raise Exception("Invalid Unique ID")

    # -----------------------
    # Load user data
    # -----------------------
    data_path = f"{user_folder}/data.json"

    if not os.path.exists(data_path):
        raise Exception("User data not found")

    with open(data_path) as f:
        user_data = json.load(f)

    # -----------------------
    # Verify masked Aadhaar
    # -----------------------
    stored_masked = user_data["masked_aadhaar"]

    stored_last4 = stored_masked[-4:]
    input_last4 = masked_aadhaar[-4:]

    if stored_last4 != input_last4:
        raise Exception("Masked Aadhaar does not match")

    # -----------------------
    # Load Aadhaar image
    # -----------------------
    aadhaar_path = f"{user_folder}/aadhaar.jpg"

    aadhaar_img = cv2.imread(aadhaar_path)

    if aadhaar_img is None:
        raise Exception("Aadhaar image not found")

    aadhaar_img = cv2.resize(aadhaar_img, (640, 640))

    aadhaar_emb = get_face_embedding(aadhaar_img)

    if aadhaar_emb is None:
        raise Exception("Face not detected in Aadhaar image")

    # -----------------------
    # Decode uploaded photo
    # -----------------------
    uploaded_img = cv2.imdecode(
        np.frombuffer(uploaded_photo, np.uint8),
        cv2.IMREAD_COLOR
    )

    if uploaded_img is None:
        raise Exception("Invalid uploaded image")

    uploaded_img = cv2.resize(uploaded_img, (640, 640))

    passport_emb = get_face_embedding(uploaded_img)

    if passport_emb is None:
        raise Exception("Face not detected in uploaded image")

    # -----------------------
    # Compare faces
    # -----------------------
    similarity = np.dot(aadhaar_emb, passport_emb) / (
        np.linalg.norm(aadhaar_emb) * np.linalg.norm(passport_emb)
    )

    similarity = float(similarity)

    if similarity < THRESHOLD:
        return {
            "status": "Face mismatch",
            "similarity": similarity
        }

    # -----------------------
    # Store passport photo locally
    # -----------------------
    passport_folder = f"{PASSPORT_STORAGE}/{unique_id}"

    os.makedirs(passport_folder, exist_ok=True)

    passport_path = f"{passport_folder}/passport.jpg"

    with open(passport_path, "wb") as f:
        f.write(uploaded_photo)

    # -----------------------
    # Upload to Cloudinary
    # -----------------------
    passport_url = upload_to_cloudinary(passport_path, folder="passports")

    # -----------------------
    # Store embedding
    # -----------------------
    os.makedirs(EMBED_STORAGE, exist_ok=True)

    embed_path = f"{EMBED_STORAGE}/{unique_id}.npy"

    np.save(embed_path, passport_emb)

    # -----------------------
    # Success response
    # -----------------------
    return {
        "status": "Face verified",
        "similarity": similarity,
        "passport_url": passport_url,
        "message": "Passport photo stored for interview verification"
    }