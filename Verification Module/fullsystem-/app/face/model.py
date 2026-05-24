from insightface.app import FaceAnalysis
import numpy as np
import cv2

face_model = None


def get_face_model():
    """
    Get or initialize the face recognition model
    Uses singleton pattern for efficiency
    """
    global face_model

    if face_model is None:
        try:
            face_model = FaceAnalysis(name="buffalo_l")
            face_model.prepare(ctx_id=0, det_size=(640, 640))  # Increased from 320x320
        except Exception as e:
            print(f"Error initializing face model: {e}")
            # Fallback to CPU if GPU fails
            try:
                face_model = FaceAnalysis(name="buffalo_l")
                face_model.prepare(ctx_id=-1, det_size=(640, 640))
            except Exception as e2:
                print(f"Error initializing face model on CPU: {e2}")
                raise

    return face_model


def get_face_embedding(image, align=True):
    """
    Extract face embedding from image
    
    Args:
        image: Input image (BGR format, numpy array)
        align: Whether to align face before embedding extraction
    
    Returns:
        Embedding vector (512-dim) or None if no face detected
    """
    
    if image is None or image.size == 0:
        return None
    
    try:
        model = get_face_model()
        
        # Ensure image is in correct format
        if len(image.shape) == 2:
            # Grayscale to BGR
            image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        elif image.shape[2] == 4:
            # RGBA to BGR
            image = cv2.cvtColor(image, cv2.COLOR_RGBA2BGR)
        
        faces = model.get(image)
        
        if len(faces) == 0:
            return None
        
        # Return the largest face (by bbox area)
        if len(faces) > 1:
            largest_face = max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))
            return largest_face.embedding
        
        return faces[0].embedding
    
    except Exception as e:
        print(f"Error extracting face embedding: {e}")
        return None


def get_all_face_embeddings(image):
    """
    Extract embeddings for all faces in image
    
    Returns:
        List of embeddings
    """
    
    if image is None or image.size == 0:
        return []
    
    try:
        model = get_face_model()
        faces = model.get(image)
        
        return [face.embedding for face in faces]
    
    except Exception as e:
        print(f"Error extracting face embeddings: {e}")
        return []


def detect_faces(image):
    """
    Detect all faces in image without extracting embeddings
    
    Returns:
        List of face bounding boxes [(x1, y1, x2, y2), ...]
    """
    
    if image is None or image.size == 0:
        return []
    
    try:
        model = get_face_model()
        faces = model.get(image)
        
        bboxes = []
        for face in faces:
            bbox = face.bbox.astype(int)
            bboxes.append((bbox[0], bbox[1], bbox[2], bbox[3]))
        
        return bboxes
    
    except Exception as e:
        print(f"Error detecting faces: {e}")
        return []


def preprocess_image_for_embedding(image, target_size=(640, 640)):
    """
    Preprocess image for optimal embedding extraction
    
    Args:
        image: Input image
        target_size: Target dimensions
    
    Returns:
        Preprocessed image
    """
    
    if image is None or image.size == 0:
        return None
    
    # Resize while maintaining aspect ratio
    h, w = image.shape[:2]
    scale = min(target_size[0] / w, target_size[1] / h)
    
    new_w = int(w * scale)
    new_h = int(h * scale)
    
    resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
    
    # Pad to target size
    top = (target_size[1] - new_h) // 2
    bottom = target_size[1] - new_h - top
    left = (target_size[0] - new_w) // 2
    right = target_size[0] - new_w - left
    
    padded = cv2.copyMakeBorder(
        resized,
        top, bottom, left, right,
        cv2.BORDER_CONSTANT,
        value=[0, 0, 0]
    )
    
    return padded