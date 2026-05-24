"""
capture_references.py
---------------------
Quickly capture diverse reference images from your webcam.
Guides you through different poses (front, left, right, up, down)
to build a robust reference set.

Usage:
    python capture_references.py [--output-dir reference_images] [--count 30]
"""

from __future__ import annotations

import os
import sys
import subprocess
import argparse
import time
from pathlib import Path

# Auto-relaunch in correct venv
venv_python = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'myenv', 'bin', 'python')
if os.path.exists(venv_python) and os.path.abspath(sys.executable) != venv_python:
    sys.exit(subprocess.call([venv_python] + sys.argv))

import cv2

POSES = [
    ("FRONT", "Look straight at the camera", 6),
    ("LEFT", "Turn your head slightly LEFT", 5),
    ("RIGHT", "Turn your head slightly RIGHT", 5),
    ("UP", "Tilt your head slightly UP", 4),
    ("DOWN", "Tilt your head slightly DOWN", 4),
    ("FRONT-CLOSE", "Move CLOSER to the camera", 3),
    ("FRONT-FAR", "Move FURTHER from the camera", 3),
]


def main():
    parser = argparse.ArgumentParser(description="Capture diverse reference images")
    parser.add_argument("--output-dir", default="reference_images", help="Output directory")
    parser.add_argument("--source", default="0", help="Camera index")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)

    source = int(args.source) if args.source.isdigit() else args.source
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        print("ERROR: Cannot open camera")
        return 1

    print("\n" + "=" * 60)
    print("  REFERENCE IMAGE CAPTURE")
    print("  This will capture images from multiple angles")
    print("  to improve face verification accuracy.")
    print("=" * 60)
    
    # Count existing images
    existing = len(list(output_dir.glob("*.jpg"))) + len(list(output_dir.glob("*.jpeg"))) + len(list(output_dir.glob("*.png")))
    print(f"\n  Existing reference images: {existing}")
    print(f"  Output directory: {output_dir}")
    print(f"\n  Press SPACE to start, ESC to cancel.\n")

    # Wait for user to press space
    while True:
        ret, frame = cap.read()
        if not ret:
            continue
        display = frame.copy()
        cv2.putText(display, "Press SPACE to start, ESC to cancel",
                    (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        cv2.imshow("Reference Capture", display)
        key = cv2.waitKey(1) & 0xFF
        if key == 27:  # ESC
            cap.release()
            cv2.destroyAllWindows()
            print("Cancelled.")
            return 0
        if key == 32:  # SPACE
            break

    total_captured = 0
    timestamp = time.strftime("%Y%m%d_%H%M%S")

    for pose_name, instruction, count in POSES:
        print(f"\n  [{pose_name}] {instruction} — capturing {count} images...")
        
        # Countdown
        for countdown in range(3, 0, -1):
            ret, frame = cap.read()
            if ret:
                display = frame.copy()
                cv2.rectangle(display, (0, 0), (display.shape[1], 50), (0, 0, 0), -1)
                cv2.putText(display, f"{instruction} - Starting in {countdown}...",
                           (10, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                cv2.imshow("Reference Capture", display)
                cv2.waitKey(1000)

        # Capture images with small delays
        for i in range(count):
            ret, frame = cap.read()
            if not ret:
                continue
            
            filename = f"ref_{timestamp}_{pose_name}_{i:02d}.jpg"
            filepath = output_dir / filename
            cv2.imwrite(str(filepath), frame)
            total_captured += 1

            # Show feedback
            display = frame.copy()
            cv2.rectangle(display, (0, 0), (display.shape[1], 50), (0, 160, 0), -1)
            cv2.putText(display, f"[{pose_name}] Captured {i+1}/{count} — {instruction}",
                       (10, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            cv2.imshow("Reference Capture", display)
            
            # Small delay between captures for slight variation
            cv2.waitKey(300)

    cap.release()
    cv2.destroyAllWindows()

    final_count = len(list(output_dir.glob("*.jpg"))) + len(list(output_dir.glob("*.jpeg"))) + len(list(output_dir.glob("*.png")))
    print(f"\n{'=' * 60}")
    print(f"  DONE! Captured {total_captured} new images.")
    print(f"  Total reference images: {final_count}")
    print(f"  Directory: {output_dir}")
    print(f"{'=' * 60}")
    print(f"\n  Now run:  python3 main.py stream --source 0 --gui\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
