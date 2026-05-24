import numpy as np

def cosine_similarity(a, b):

    a = np.asarray(a, dtype=np.float32)
    b = np.asarray(b, dtype=np.float32)

    # add epsilon to avoid division by zero
    eps = 1e-10

    norm_a = np.linalg.norm(a) + eps
    norm_b = np.linalg.norm(b) + eps

    a = a / norm_a
    b = b / norm_b

    similarity = np.dot(a, b)

    # clip to avoid floating precision overflow
    similarity = np.clip(similarity, -1.0, 1.0)

    return float(similarity)