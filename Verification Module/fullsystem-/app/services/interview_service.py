import cv2
import numpy as np
import mediapipe as mp
import os
from collections import deque
from datetime import datetime, timedelta

from app.face.model import get_face_embedding
from app.face.utils import cosine_similarity
from app.liveness.gaze_detector import get_eye_direction
from app.liveness.screen_detector import detect_screen
from app.liveness.blink_detector import detect_blink

EMBED_STORAGE = "app/storage/embeddings"

# Configuration
THRESHOLD = 0.40 
MIN_FRAMES_FOR_VERIFICATION = 7  
DIRECTION_STABLE_FRAMES = 3  
MAX_SESSION_DURATION = 120  
MAX_COMPLETED_SESSION_DURATION = 300  # 5 minutes - completed sessions expire after this
BLINK_REQUIRED = True  

# Session storage
class SessionData:
    def __init__(self):
        self.step = "LOOK_LEFT"
        self.frame_buffer = deque(maxlen=MIN_FRAMES_FOR_VERIFICATION)
        self.direction_counter = {"LEFT": 0, "RIGHT": 0, "CENTER": 0}
        self.last_direction = None
        self.blink_detected = False
        self.created_at = datetime.now()
        self.face_quality_scores = []

# NEW: Wrapper for completed sessions with timestamp
class CompletedSessionData:
    def __init__(self, result):
        self.result = result
        self.completed_at = datetime.now()
       
sessions = {}
completed_sessions = {}


def cleanup_expired_sessions():
    """Remove sessions older than MAX_SESSION_DURATION"""
    current_time = datetime.now()
    expired = []
   
    # Clean up active sessions
    for uid, session in sessions.items():
        if (current_time - session.created_at).total_seconds() > MAX_SESSION_DURATION:
            expired.append(uid)
   
    for uid in expired:
        sessions.pop(uid, None)
   
    # NEW: Clean up completed sessions older than MAX_COMPLETED_SESSION_DURATION
    expired_completed = []
    for uid, completed_data in completed_sessions.items():
        if (current_time - completed_data.completed_at).total_seconds() > MAX_COMPLETED_SESSION_DURATION:
            expired_completed.append(uid)
   
    for uid in expired_completed:
        completed_sessions.pop(uid, None)
       

def calculate_face_quality(face_img):
    """Calculate face quality based on sharpness and size"""
    if face_img is None or face_img.size == 0:
        return 0.0
   
    gray = cv2.cvtColor(face_img, cv2.COLOR_BGR2GRAY)
   
    # Laplacian variance for sharpness
    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
   
    # Normalize sharpness score (typical range 0-500)
    sharpness_score = min(laplacian_var / 500.0, 1.0)
   
    # Size score (prefer larger faces)
    h, w = face_img.shape[:2]
    size_score = min((h * w) / (112 * 112), 1.0)
   
    # Combined quality score
    quality = (sharpness_score * 0.7 + size_score * 0.3)
   
    return quality


def verify_with_multiple_frames(stored_emb, frame_buffer, unique_id):
    """
    Verify face using multiple frames for better accuracy
    IMPROVED: Uses full frames with face detection instead of pre-cropped faces
    """
   
    if len(frame_buffer) < MIN_FRAMES_FOR_VERIFICATION:
        return None, "Collecting frames..."
   
    similarities = []
    successful_frames = 0
   
    for frame_data in frame_buffer:
        # Use the FULL frame, not the cropped face
        full_frame = frame_data['full_frame']
        face_box = frame_data['face_box']
        quality = frame_data['quality']
       
        # Validate frame
        if full_frame is None or full_frame.size == 0:
            continue
       
        # Resize full frame for consistent processing
        h, w = full_frame.shape[:2]
       
        # Scale to a reasonable size (max 1280 width)
        if w > 1280:
            scale = 1280 / w
            new_w = 1280
            new_h = int(h * scale)
            full_frame = cv2.resize(full_frame, (new_w, new_h))
       
        # Get embedding from FULL FRAME (InsightFace will detect face automatically)
        current_emb = get_face_embedding(full_frame)
       
        if current_emb is not None:
            similarity = cosine_similarity(stored_emb, current_emb)
           
            # Weight similarity by face quality
            weighted_similarity = similarity * (0.7 + 0.3 * quality)
           
            similarities.append(weighted_similarity)
            successful_frames += 1
   
    # Need at least 3 successful frames (60% of 5)
    if successful_frames < 3:
        return None, f"Face not clear (only {successful_frames}/{len(frame_buffer)} frames processed)"
   
    # Use median similarity (more robust than mean)
    median_similarity = float(np.median(similarities))
   
    # Also check average of top 60% frames
    top_k = max(2, int(len(similarities) * 0.6))
    sorted_sims = sorted(similarities, reverse=True)
    top_avg = float(np.mean(sorted_sims[:top_k]))
   
    # Final similarity is weighted combination
    final_similarity = 0.6 * median_similarity + 0.4 * top_avg
   
    return final_similarity, None


def process_face_landmarks(frame):
    """
    Process frame and extract face landmarks using MediaPipe
    Creates and destroys FaceMesh instance to avoid camera lock
   
    Returns:
        (landmarks, face_box) or (None, None) if no face detected
    """
   
    if frame is None or frame.size == 0:
        return None, None
   
    h, w, _ = frame.shape
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
   
    # Create fresh FaceMesh instance (will be auto-released when function exits)
    mp_face_mesh = mp.solutions.face_mesh
   
    # Use context manager to ensure proper cleanup
    with mp_face_mesh.FaceMesh(
        static_image_mode=True,  # For single images (no video stream)
        max_num_faces=1,
        refine_landmarks=True,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    ) as face_mesh:
       
        result = face_mesh.process(rgb)
       
        if not result.multi_face_landmarks:
            return None, None
       
        landmarks = result.multi_face_landmarks[0].landmark
       
        # Calculate face bounding box with better margins
        xs = [lm.x for lm in landmarks]
        ys = [lm.y for lm in landmarks]
       
        # Get tight bbox first
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
       
        # Add padding (15% on each side) for better face crop
        width = max_x - min_x
        height = max_y - min_y
       
        pad_x = width * 0.15
        pad_y = height * 0.15
       
        # Apply padding
        min_x = max(0, min_x - pad_x)
        max_x = min(1.0, max_x + pad_x)
        min_y = max(0, min_y - pad_y)
        max_y = min(1.0, max_y + pad_y)
       
        # Convert to pixel coordinates
        x1 = max(0, int(min_x * w))
        y1 = max(0, int(min_y * h))
        x2 = min(w, int(max_x * w))
        y2 = min(h, int(max_y * h))
       
        # Validate bounding box
        if x2 <= x1 or y2 <= y1:
            return None, None
       
        # Ensure minimum size
        if (x2 - x1) < 60 or (y2 - y1) < 60:
            return None, None
       
        face_box = [x1, y1, x2, y2]
       
        return landmarks, face_box


def verify_interview(unique_id, webcam_image):
    """
    Main interview verification function with multi-frame support
    FIXED: No camera lock issues + Uses full frames for embedding
    """
   
    # Clean up old sessions periodically
    cleanup_expired_sessions()
   
    # UPDATED: Check if already completed and return result from wrapper
    if unique_id in completed_sessions:
        return completed_sessions[unique_id].result
   
    # Check if user exists
    embed_path = f"{EMBED_STORAGE}/{unique_id}.npy"
    if not os.path.exists(embed_path):
        return {"status": "User not found", "error": True}
   
    # Decode frame
    frame = cv2.imdecode(
        np.frombuffer(webcam_image, np.uint8),
        cv2.IMREAD_COLOR
    )
   
    if frame is None:
        return {"status": "Invalid image", "error": True}
   
    # Process face with MediaPipe (creates and destroys instance)
    landmarks, face_box = process_face_landmarks(frame)
   
    if landmarks is None or face_box is None:
        return {"status": "Face not detected", "instruction": "Position your face in the frame"}
   
    # Initialize or get session
    if unique_id not in sessions:
        sessions[unique_id] = SessionData()
   
    session = sessions[unique_id]
   
    # Detect blink for liveness
    if detect_blink(landmarks):
        session.blink_detected = True
   
    # Get current gaze direction
    direction = get_eye_direction(landmarks)
   
    # Update direction counter for stability
    if direction == session.last_direction:
        session.direction_counter[direction] = session.direction_counter.get(direction, 0) + 1
    else:
        session.direction_counter = {"LEFT": 0, "RIGHT": 0, "CENTER": 0}
        session.direction_counter[direction] = 1
        session.last_direction = direction
   
    current_step = session.step
   
    # ==========================================
    # STEP 1: LOOK LEFT
    # ==========================================
    if current_step == "LOOK_LEFT":
       
        if direction == "LEFT" and session.direction_counter["LEFT"] >= DIRECTION_STABLE_FRAMES:
            session.step = "LOOK_RIGHT"
            session.direction_counter = {"LEFT": 0, "RIGHT": 0, "CENTER": 0}
           
            return {
                "status": "Good! Now look RIGHT",
                "face_box": face_box,
                "progress": "1/3"
            }
       
        return {
            "status": "Look LEFT",
            "face_box": face_box,
            "instruction": "Move your eyes to the left",
            "progress": "1/3"
        }
   
    # ==========================================
    # STEP 2: LOOK RIGHT
    # ==========================================
    elif current_step == "LOOK_RIGHT":
       
        if direction == "RIGHT" and session.direction_counter["RIGHT"] >= DIRECTION_STABLE_FRAMES:
            session.step = "LOOK_CENTER"
            session.direction_counter = {"LEFT": 0, "RIGHT": 0, "CENTER": 0}
           
            return {
                "status": "Good! Now look at the CAMERA",
                "face_box": face_box,
                "progress": "2/3"
            }
       
        return {
            "status": "Look RIGHT",
            "face_box": face_box,
            "instruction": "Move your eyes to the right",
            "progress": "2/3"
        }
   
    # ==========================================
    # STEP 3: LOOK CENTER & COLLECT FRAMES
    # ==========================================
    elif current_step == "LOOK_CENTER":
       
        if direction == "CENTER" and session.direction_counter["CENTER"] >= DIRECTION_STABLE_FRAMES:
           
            # Extract face region for quality check
            x1, y1, x2, y2 = face_box
            face_crop = frame[y1:y2, x1:x2]
           
            if face_crop.size == 0:
                return {
                    "status": "Look at the camera",
                    "face_box": face_box,
                    "instruction": "Keep your face in the frame",
                    "progress": "3/3"
                }
           
            # Calculate face quality
            quality = calculate_face_quality(face_crop)
           
            # NEW: Check for screen BEFORE adding to buffer (early detection)
            if detect_screen(face_crop, aggressive=False):
                return {
                    "status": "Screen detected",
                    "face_box": face_box,
                    "instruction": "Please use a real webcam, not a photo or screen",
                    "error": True
                }
           
            # Add to frame buffer - STORE FULL FRAME not just crop
            session.frame_buffer.append({
                'full_frame': frame.copy(),  # Store full frame!
                'face_box': face_box,
                'quality': quality,
                'timestamp': datetime.now()
            })
           
            # Check if we have enough frames
            buffer_size = len(session.frame_buffer)
           
            if buffer_size < MIN_FRAMES_FOR_VERIFICATION:
                return {
                    "status": f"Hold steady... ({buffer_size}/{MIN_FRAMES_FOR_VERIFICATION})",
                    "face_box": face_box,
                    "instruction": "Keep looking at the camera",
                    "progress": "3/3"
                }
           
            # We have enough frames - perform verification
           
            # First: Check for screen spoofing - STRICTER CHECK
            screen_detected_count = 0
            for frame_data in session.frame_buffer:
                # Use the face region for screen detection
                full = frame_data['full_frame']
                box = frame_data['face_box']
                test_region = full[box[1]:box[3], box[0]:box[2]]
               
                if detect_screen(test_region):
                    screen_detected_count += 1
           
            # STRICTER: If ANY frame shows screen characteristics, reject
            # Changed from 40% to 20% tolerance
            if screen_detected_count > len(session.frame_buffer) * 0.2:
                result = {
                    "status": "Verification Failed",
                    "reason": f"Mobile screen or photo detected in {screen_detected_count}/{len(session.frame_buffer)} frames",
                    "error": True
                }
               
                # Clean up
                sessions.pop(unique_id, None)
                # UPDATED: Store in wrapper with timestamp
                completed_sessions[unique_id] = CompletedSessionData(result)
               
                return result
           
            # Second: Check blink detection (liveness)
            if BLINK_REQUIRED and not session.blink_detected:
                return {
                    "status": "Please blink once",
                    "face_box": face_box,
                    "instruction": "Blink naturally to confirm liveness",
                    "progress": "3/3"
                }
           
            # Third: Perform face verification with multiple frames
            stored_emb = np.load(embed_path)
           
            final_similarity, error_msg = verify_with_multiple_frames(
                stored_emb,
                session.frame_buffer,
                unique_id
            )
           
            if error_msg:
                return {
                    "status": error_msg,
                    "face_box": face_box,
                    "instruction": "Ensure good lighting and face visibility"
                }
           
            # Clean up session
            sessions.pop(unique_id, None)
           
            # Check threshold
            if final_similarity < THRESHOLD:
                result = {
                    "status": "Verification Failed",
                    "reason": "Face does not match registered photo",
                    "similarity": final_similarity,
                    "error": True
                }
               
                # UPDATED: Store in wrapper with timestamp
                completed_sessions[unique_id] = CompletedSessionData(result)
                return result
           
            # SUCCESS!
            result = {
                "status": "Verification Successful",
                "similarity": final_similarity,
                "message": "Identity verified successfully",
                "verified": True
            }
           
            # UPDATED: Store in wrapper with timestamp
            completed_sessions[unique_id] = CompletedSessionData(result)
            return result
       
        # Still waiting for stable center gaze
        return {
            "status": "Look at the camera",
            "face_box": face_box,
            "instruction": "Keep your eyes on the camera",
            "progress": "3/3"
        }
   
    # Fallback
    return {
        "status": "Unknown state",
        "error": True
    }


def reset_verification(unique_id):
    """Reset verification for a user (useful for retry)"""
    sessions.pop(unique_id, None)
    completed_sessions.pop(unique_id, None)
   
    return {"status": "Verification reset", "message": "You can try again"}


def get_verification_status(unique_id):
    """Get current verification status without processing a frame"""
   
    # UPDATED: Return result from wrapper
    if unique_id in completed_sessions:
        return completed_sessions[unique_id].result
   
    if unique_id in sessions:
        session = sessions[unique_id]
        return {
            "status": "In progress",
            "current_step": session.step,
            "frames_collected": len(session.frame_buffer),
            "blink_detected": session.blink_detected
        }
   
    return {"status": "Not started"}

    