import cv2
import numpy as np

from app.face.model import get_face_embedding
from app.face.utils import cosine_similarity

THRESHOLD = 0.65


def compare_faces(img1, img2):

    if img1 is None or img2 is None:
        return False, 0

    # normalize image size for stable embeddings
    img1 = cv2.resize(img1, (224, 224))
    img2 = cv2.resize(img2, (224, 224))

    emb1 = get_face_embedding(img1)
    emb2 = get_face_embedding(img2)

    if emb1 is None or emb2 is None:
        return False, 0

    # normalize embeddings
    emb1 = emb1 / np.linalg.norm(emb1)
    emb2 = emb2 / np.linalg.norm(emb2)

    similarity = cosine_similarity(emb1, emb2)

    verified = similarity >= THRESHOLD

    return verified, float(similarity)