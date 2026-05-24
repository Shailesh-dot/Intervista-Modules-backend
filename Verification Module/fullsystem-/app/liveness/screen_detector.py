import cv2
import numpy as np


def detect_screen(frame, aggressive=True):
    """
    Detect if the image is from a phone/monitor screen using multiple techniques
    ENHANCED for mobile phone screen detection during interviews
   
    Args:
        frame: Input image (BGR format)
        aggressive: If True, uses stricter thresholds (DEFAULT: True for security)
   
    Returns:
        True if screen detected, False otherwise
    """
   
    if frame is None or frame.size == 0:
        return False
   
    # Combine multiple detection methods for robustness
    screen_indicators = 0
    total_checks = 0
   
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
   
    # ========================================
    # 1. Laplacian Variance (Sharpness)
    # ========================================
    # Phone screens typically have lower sharpness due to re-capture
    lap_var = cv2.Laplacian(gray, cv2.CV_64F).var()
   
    # Aggressive mode should have a HIGHER threshold to flag more potential screens
    threshold = 130 if aggressive else 80
    if lap_var < threshold:
        screen_indicators += 1
    total_checks += 1
   
    # ========================================
    # 2. Moiré Pattern Detection (FFT)
    # ========================================
    # Screens create interference patterns when photographed
    try:
        # Use smaller region for faster computation
        h, w = gray.shape
        center_crop = gray[h//4:3*h//4, w//4:3*w//4]
       
        dft = cv2.dft(np.float32(center_crop), flags=cv2.DFT_COMPLEX_OUTPUT)
        dft_shift = np.fft.fftshift(dft)
        magnitude = cv2.magnitude(dft_shift[:,:,0], dft_shift[:,:,1])
       
        h_crop, w_crop = magnitude.shape
        center_h, center_w = h_crop//2, w_crop//2
       
        # Exclude DC component
        mask = np.ones((h_crop, w_crop), dtype=np.uint8)
        cv2.circle(mask, (center_w, center_h), 20, 0, -1)
       
        high_freq_energy = np.mean(magnitude[mask == 1])
        low_freq_energy = np.mean(magnitude[mask == 0])
       
        ratio = high_freq_energy / (low_freq_energy + 1e-6)
       
        # Screens show higher high-frequency patterns
        if ratio > 0.10:
            screen_indicators += 1
        total_checks += 1
    except:
        pass
   
    # ========================================
    # 3. Brightness Uniformity
    # ========================================
    # Screens have more uniform brightness than real faces
    brightness_std = np.std(gray)
   
    # Real faces: std > 35, Screens: std < 30
    if brightness_std < 25:
        screen_indicators += 1
    total_checks += 1
   
    # ========================================
    # 4. RGB Channel Correlation
    # ========================================
    # Screens have unnatural color correlation
    b, g, r = cv2.split(frame)
   
    r_flat = r.flatten().astype(float)
    g_flat = g.flatten().astype(float)
    b_flat = b.flatten().astype(float)
   
    # High correlation = screen
    rg_corr = np.corrcoef(r_flat, g_flat)[0, 1]
    rb_corr = np.corrcoef(r_flat, b_flat)[0, 1]
    gb_corr = np.corrcoef(g_flat, b_flat)[0, 1]
   
    avg_corr = (rg_corr + rb_corr + gb_corr) / 3
   
    if avg_corr > 0.93:
        screen_indicators += 1
    total_checks += 1
   
    # ========================================
    # 5. Color Saturation Analysis
    # ========================================
    # Screens often have different saturation characteristics
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    saturation = hsv[:,:,1]
    sat_std = np.std(saturation)
   
    # Low variance in saturation = screen
    if sat_std < 38:
        screen_indicators += 1
    total_checks += 1
   
    # ========================================
    # 6. Edge Characteristics
    # ========================================
    # Screens have unusual edge patterns
    edges = cv2.Canny(gray, 40, 120)
    edge_density = np.sum(edges > 0) / edges.size
   
    # Anomalous edge density
    if edge_density < 0.04 or edge_density > 0.18:
        screen_indicators += 1
    total_checks += 1
   
    # ========================================
    # 7. Gradient Regularity
    # ========================================
    # Screens have more regular gradients
    sobel_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    sobel_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
   
    grad_x_std = np.std(sobel_x)
    grad_y_std = np.std(sobel_y)
   
    # Low gradient variance = regular pattern = screen
    if grad_x_std < 28 or grad_y_std < 28:
        screen_indicators += 1
    total_checks += 1
   
    # ========================================
    # 8. Texture Analysis (LBP-inspired)
    # ========================================
    # Real skin has different texture than screen-displayed face
    # Simple texture variance check
    kernel_size = 5
    kernel = np.ones((kernel_size, kernel_size), np.float32) / (kernel_size**2)
    local_mean = cv2.filter2D(gray.astype(float), -1, kernel)
    local_var = cv2.filter2D((gray.astype(float) - local_mean)**2, -1, kernel)
   
    texture_variance = np.mean(local_var)
   
    # Screens have lower texture variance
    if texture_variance < 60:
        screen_indicators += 1
    total_checks += 1
   
    # ========================================
    # 9. Specular Highlights Check
    # ========================================
    # Screens often have glare/reflections
    bright_pixels = np.sum(gray > 235)
    total_pixels = gray.size
    bright_ratio = bright_pixels / total_pixels
   
    # Excessive bright pixels = screen reflection
    if bright_ratio > 0.08:
        screen_indicators += 1
    total_checks += 1
   
    # ========================================
    # Final Decision - STRICT
    # ========================================
    # Require at least 4 out of 9 indicators for aggressive mode
    required_indicators = 4 if aggressive else 5
   
    is_screen = screen_indicators >= required_indicators
   
    return is_screen


def detect_screen_with_confidence(frame):
    """
    Detect screen with confidence score
   
    Returns:
        Tuple of (is_screen, confidence)
        is_screen: Boolean
        confidence: 0.0 to 1.0
    """
   
    if frame is None or frame.size == 0:
        return False, 0.0
   
    indicators = []
   
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
   
    # 1. Laplacian variance
    lap_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    lap_score = max(0, min(1, (110 - lap_var) / 110))
    indicators.append(lap_score)
   
    # 2. Brightness uniformity
    brightness_std = np.std(gray)
    brightness_score = max(0, min(1, (40 - brightness_std) / 40))
    indicators.append(brightness_score)
   
    # 3. Saturation variance
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    sat_std = np.std(hsv[:,:,1])
    sat_score = max(0, min(1, (45 - sat_std) / 45))
    indicators.append(sat_score)
   
    # 4. RGB correlation
    b, g, r = cv2.split(frame)
    rg_corr = np.corrcoef(r.flatten(), g.flatten())[0, 1]
    corr_score = max(0, (rg_corr - 0.85) / 0.15)
    indicators.append(corr_score)
   
    # Average confidence
    confidence = np.mean(indicators)
   
    # Decision threshold
    is_screen = confidence > 0.55
   
    return is_screen, confidence


def detect_reflection(frame):
    """
    Detect specular reflections common in photos of screens
   
    Returns:
        True if strong reflections detected
    """
   
    if frame is None or frame.size == 0:
        return False
   
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
   
    # Threshold for very bright pixels (potential reflections)
    bright_pixels = np.sum(gray > 240)
    total_pixels = gray.size
   
    bright_ratio = bright_pixels / total_pixels
   
    # More than 5% very bright pixels suggests reflections
    return bright_ratio > 0.05


def is_print_attack(frame):
    """
    Detect if image is a printed photo being shown to camera
   
    Returns:
        True if print attack detected
    """
   
    if frame is None or frame.size == 0:
        return False
   
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
   
    # Printed photos have:
    # 1. Very low frequency content (smooth)
    # 2. Limited dynamic range
    # 3. Uniform texture
   
    # Check dynamic range
    pixel_range = np.max(gray) - np.min(gray)
   
    # Check standard deviation
    std_dev = np.std(gray)
   
    # Prints typically have limited range and low std
    if pixel_range < 150 and std_dev < 25:
        return True
   
    return False