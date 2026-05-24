import numpy as np

# MediaPipe Face Mesh landmark indices
LEFT_EYE_TOP = 159
LEFT_EYE_BOTTOM = 145
RIGHT_EYE_TOP = 386
RIGHT_EYE_BOTTOM = 374

# Eye aspect ratio calculation points
LEFT_EYE_VERTICAL = [(159, 145), (158, 153)]  # Multiple vertical distances
RIGHT_EYE_VERTICAL = [(386, 374), (385, 380)]

def calculate_eye_aspect_ratio(landmarks, eye_points):
    """
    Calculate Eye Aspect Ratio (EAR) using multiple vertical measurements
    More robust than single point measurement
    """
    vertical_distances = []
    
    for top_idx, bottom_idx in eye_points:
        top = landmarks[top_idx]
        bottom = landmarks[bottom_idx]
        
        # Calculate Euclidean distance
        distance = np.sqrt(
            (top.x - bottom.x)**2 + 
            (top.y - bottom.y)**2 + 
            (top.z - bottom.z)**2
        )
        vertical_distances.append(distance)
    
    # Average vertical distance
    avg_vertical = np.mean(vertical_distances)
    
    return avg_vertical


def detect_blink(landmarks, threshold=0.016):
    """
    Detect blink using bilateral eye closure detection
    
    Args:
        landmarks: MediaPipe face mesh landmarks
        threshold: EAR threshold for blink detection (lower = eyes more closed)
    
    Returns:
        True if blink detected, False otherwise
    """
    
    # Calculate EAR for both eyes
    left_ear = calculate_eye_aspect_ratio(landmarks, LEFT_EYE_VERTICAL)
    right_ear = calculate_eye_aspect_ratio(landmarks, RIGHT_EYE_VERTICAL)
    
    # Average EAR (more robust)
    avg_ear = (left_ear + right_ear) / 2.0
    
    # Blink detected if EAR below threshold
    # Both eyes should be closed for valid blink
    if avg_ear < threshold and left_ear < threshold * 1.2 and right_ear < threshold * 1.2:
        return True
    
    return False


def detect_blink_sequence(landmarks_history, min_sequence_length=3):
    """
    Detect a blink sequence (close -> open pattern)
    More sophisticated than single frame detection
    
    Args:
        landmarks_history: List of recent landmark sets
        min_sequence_length: Minimum frames for valid blink sequence
    
    Returns:
        True if valid blink sequence detected
    """
    
    if len(landmarks_history) < min_sequence_length:
        return False
    
    # Calculate EAR for recent frames
    ear_values = []
    for landmarks in landmarks_history[-5:]:  # Check last 5 frames
        left_ear = calculate_eye_aspect_ratio(landmarks, LEFT_EYE_VERTICAL)
        right_ear = calculate_eye_aspect_ratio(landmarks, RIGHT_EYE_VERTICAL)
        avg_ear = (left_ear + right_ear) / 2.0
        ear_values.append(avg_ear)
    
    # Look for close-open pattern
    # EAR should dip below threshold then rise above it
    threshold = 0.016
    open_threshold = 0.022
    
    min_ear = min(ear_values)
    max_ear = max(ear_values)
    
    # Valid blink: goes below close threshold and returns above open threshold
    if min_ear < threshold and max_ear > open_threshold:
        # Check for proper sequence (not just noise)
        below_count = sum(1 for ear in ear_values if ear < threshold)
        above_count = sum(1 for ear in ear_values if ear > open_threshold)
        
        if below_count >= 1 and above_count >= 1:
            return True
    
    return False