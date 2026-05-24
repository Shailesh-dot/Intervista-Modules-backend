import numpy as np

# MediaPipe Face Mesh landmark indices for left eye
LEFT_EYE_LEFT = 33
LEFT_EYE_RIGHT = 133
LEFT_IRIS = 468

# MediaPipe Face Mesh landmark indices for right eye
RIGHT_EYE_LEFT = 362
RIGHT_EYE_RIGHT = 263
RIGHT_IRIS = 473


def get_eye_direction(landmarks, sensitivity=0.15):
    """
    Detect eye gaze direction using iris position relative to eye corners
    Uses both eyes for more robust detection
    
    Args:
        landmarks: MediaPipe face mesh landmarks
        sensitivity: How sensitive the detection is (0.1-0.25 recommended)
                    Lower = more sensitive, Higher = requires more extreme gaze
    
    Returns:
        "LEFT", "RIGHT", or "CENTER"
    """
    
    # Left eye analysis
    left_iris_x = landmarks[LEFT_IRIS].x
    left_corner_left = landmarks[LEFT_EYE_LEFT].x
    left_corner_right = landmarks[LEFT_EYE_RIGHT].x
    
    # Calculate ratio (0 = looking left, 1 = looking right)
    left_eye_width = left_corner_right - left_corner_left
    if left_eye_width > 0:
        left_ratio = (left_iris_x - left_corner_left) / left_eye_width
    else:
        left_ratio = 0.5
    
    # Right eye analysis
    right_iris_x = landmarks[RIGHT_IRIS].x
    right_corner_left = landmarks[RIGHT_EYE_LEFT].x
    right_corner_right = landmarks[RIGHT_EYE_RIGHT].x
    
    right_eye_width = right_corner_right - right_corner_left
    if right_eye_width > 0:
        right_ratio = (right_iris_x - right_corner_left) / right_eye_width
    else:
        right_ratio = 0.5
    
    # Average both eyes for robustness
    avg_ratio = (left_ratio + right_ratio) / 2.0
    
    # Determine direction with configurable thresholds
    center_min = 0.5 - sensitivity
    center_max = 0.5 + sensitivity
    
    if avg_ratio < center_min:
        return "RIGHT"
    elif avg_ratio > center_max:
        return "LEFT"
    else:
        return "CENTER"


def get_eye_direction_with_confidence(landmarks, sensitivity=0.15):
    """
    Get eye direction with confidence score
    
    Returns:
        Tuple of (direction, confidence)
        direction: "LEFT", "RIGHT", or "CENTER"
        confidence: 0.0 to 1.0 indicating how clear the direction is
    """
    
    # Calculate ratios for both eyes
    left_iris_x = landmarks[LEFT_IRIS].x
    left_corner_left = landmarks[LEFT_EYE_LEFT].x
    left_corner_right = landmarks[LEFT_EYE_RIGHT].x
    
    left_eye_width = left_corner_right - left_corner_left
    if left_eye_width > 0:
        left_ratio = (left_iris_x - left_corner_left) / left_eye_width
    else:
        left_ratio = 0.5
    
    right_iris_x = landmarks[RIGHT_IRIS].x
    right_corner_left = landmarks[RIGHT_EYE_LEFT].x
    right_corner_right = landmarks[RIGHT_EYE_RIGHT].x
    
    right_eye_width = right_corner_right - right_corner_left
    if right_eye_width > 0:
        right_ratio = (right_iris_x - right_corner_left) / right_eye_width
    else:
        right_ratio = 0.5
    
    # Average ratio
    avg_ratio = (left_ratio + right_ratio) / 2.0
    
    # Calculate how far from center (0.5)
    deviation_from_center = abs(avg_ratio - 0.5)
    
    # Confidence based on deviation
    # More deviation = more confident in LEFT/RIGHT
    # Less deviation = more confident in CENTER
    
    center_min = 0.5 - sensitivity
    center_max = 0.5 + sensitivity
    
    if avg_ratio < center_min:
        direction = "RIGHT"
        # Confidence increases with distance from center_min
        confidence = min(1.0, deviation_from_center / 0.3)
    elif avg_ratio > center_max:
        direction = "LEFT"
        confidence = min(1.0, deviation_from_center / 0.3)
    else:
        direction = "CENTER"
        # For center, confidence is inverse of deviation
        confidence = max(0.0, 1.0 - (deviation_from_center / sensitivity))
    
    return direction, confidence


def smooth_gaze_detection(landmarks_history, window_size=5):
    """
    Smooth gaze detection over multiple frames to reduce jitter
    
    Args:
        landmarks_history: List of recent landmark sets
        window_size: Number of frames to average over
    
    Returns:
        Smoothed direction: "LEFT", "RIGHT", or "CENTER"
    """
    
    if len(landmarks_history) < 2:
        if landmarks_history:
            return get_eye_direction(landmarks_history[-1])
        return "CENTER"
    
    # Get directions for recent frames
    recent_frames = landmarks_history[-window_size:]
    directions = []
    
    for landmarks in recent_frames:
        direction = get_eye_direction(landmarks)
        directions.append(direction)
    
    # Count occurrences
    left_count = directions.count("LEFT")
    right_count = directions.count("RIGHT")
    center_count = directions.count("CENTER")
    
    # Return majority direction
    if left_count > right_count and left_count > center_count:
        return "RIGHT"
    elif right_count > left_count and right_count > center_count:
        return "LEFT"
    else:
        return "CENTER"