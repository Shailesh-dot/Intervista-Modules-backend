def detect_head_direction(landmarks):

    nose = landmarks[1]

    if nose.x < 0.40:
        return "RIGHT"

    elif nose.x > 0.60:
        return "LEFT"

    else:
        return "CENTER"