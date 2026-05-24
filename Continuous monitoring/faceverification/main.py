"""
main.py
-------
Command-line interface for the Face Authorisation System.

Modes
-----
  image   – verify a single image file
  stream  – continuous verification from webcam / RTSP feed
  batch   – verify every image inside a directory

Usage examples
--------------
  python main.py image  --input photo.jpg
  python main.py stream --source 0
  python main.py batch  --input-dir test_frames/
"""

from __future__ import annotations

import os
import sys
import subprocess

# Auto-relaunch in the correct virtual environment if available
venv_python = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'myenv', 'bin', 'python')
if os.path.exists(venv_python) and os.path.abspath(sys.executable) != venv_python:
    sys.exit(subprocess.call([venv_python] + sys.argv))

import argparse
import logging
import time
from pathlib import Path

from config import EngineConfig
from face_engine import FaceAuthEngine, AuthStatus
from audit_logger import AuditLogger
from stream_verifier import StreamVerifier


# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

def _setup_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s – %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )


# ---------------------------------------------------------------------------
# CLI handlers
# ---------------------------------------------------------------------------

def cmd_image(args, cfg: EngineConfig, engine: FaceAuthEngine, auditor: AuditLogger) -> int:
    """Verify a single image file."""
    result = engine.verify_image_path(args.input)
    auditor.log(result, source=str(args.input))

    _print_result(result)
    return 0 if result.authorised else 1


def cmd_batch(args, cfg: EngineConfig, engine: FaceAuthEngine, auditor: AuditLogger) -> int:
    """Verify all images in a directory."""
    input_dir = Path(args.input_dir)
    if not input_dir.is_dir():
        logging.error("Input directory not found: %s", input_dir)
        return 2

    extensions = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"}
    images = [p for p in sorted(input_dir.iterdir()) if p.suffix.lower() in extensions]

    if not images:
        logging.warning("No images found in %s", input_dir)
        return 0

    print(f"\n{'─'*60}")
    print(f"  Batch verification – {len(images)} image(s)")
    print(f"{'─'*60}")

    passed = failed = 0
    for img_path in images:
        result = engine.verify_image_path(img_path)
        auditor.log(result, source=str(img_path))
        tag = "✓ PASS" if result.authorised else "✗ FAIL"
        conf_str = f"{result.confidence:.3f}" if result.confidence is not None else "N/A"
        print(f"  {tag}  {img_path.name:<40}  status={result.status.name:<20}  conf={conf_str}")
        if result.authorised:
            passed += 1
        else:
            failed += 1

    print(f"{'─'*60}")
    print(f"  Results: {passed} passed, {failed} failed\n")
    return 0 if failed == 0 else 1


def cmd_stream(args, cfg: EngineConfig, engine: FaceAuthEngine, auditor: AuditLogger) -> int:
    """Continuous verification from webcam / RTSP stream."""

    def on_result(result):
        auditor.log(result, source=str(args.source))
        _print_result(result, compact=True)

    def on_error(exc):
        logging.critical("Stream error: %s", exc)

    source = args.source
    # Convert to int if it's a digit (camera index)
    if isinstance(source, str) and source.isdigit():
        source = int(source)

    verifier = StreamVerifier(
        engine=engine,
        source=source,
        fps_cap=cfg.stream_fps_cap,
        on_result=on_result,
        on_error=on_error,
    )

    print(f"\n[STREAM] Starting verification on source: {source}")
    print("[STREAM] Press Ctrl+C to stop.\n")

    try:
        if getattr(args, "gui", False):
            import cv2

        with verifier:
            while True:
                if getattr(args, "gui", False):
                    frame = verifier.latest_frame
                    if frame is not None:
                        result = verifier.latest_result
                        
                        # Draw face bounding box
                        if result and result.face_location:
                            fl = result.face_location
                            if result.status == AuthStatus.MULTIPLE_FACES:
                                color = (0, 200, 255)  # Yellow
                                label = "MULTIPLE FACES"
                            elif result.authorised:
                                color = (0, 220, 0)    # Green
                                label = "AUTHORISED"
                            elif result.status == AuthStatus.UNAUTHORISED:
                                color = (0, 0, 220)    # Red
                                label = "UNAUTHORISED"
                            else:
                                color = (0, 200, 255)  # Yellow/Amber
                                label = "IDENTIFYING"
                            
                            # Draw thick rectangle
                            cv2.rectangle(frame, (fl.left, fl.top), (fl.right, fl.bottom), color, 3)
                            
                            # Confidence text
                            conf_str = f" ({result.confidence:.0%})" if result.confidence else ""
                            cv2.putText(frame, f"{label}{conf_str}", 
                                       (fl.left, max(25, fl.top - 12)),
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
                        
                        # Status bar at top (MULTIPLE_FACES takes priority)
                        if result:
                            if result.status == AuthStatus.MULTIPLE_FACES:
                                bar_color = (0, 180, 220)   # Yellow
                            elif result.authorised:
                                bar_color = (0, 160, 0)     # Green
                            elif result.status == AuthStatus.UNAUTHORISED:
                                bar_color = (0, 0, 160)     # Red
                            else:
                                bar_color = (0, 140, 180)   # Amber
                            cv2.rectangle(frame, (0, 0), (frame.shape[1], 35), bar_color, -1)
                            status_text = result.message or result.status.name
                            cv2.putText(frame, status_text, (10, 25),
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                        
                        cv2.imshow("Face Auth (ESC to exit)", frame)
                    
                    # waitKey(1) for maximum GUI responsiveness
                    if cv2.waitKey(1) & 0xFF == 27:
                        break
                else:
                    time.sleep(1)
    except KeyboardInterrupt:
        print("\n[STREAM] Stopped by user.")
    finally:
        if getattr(args, "gui", False):
            try:
                import cv2
                cv2.destroyAllWindows()
            except ImportError:
                pass

    return 0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _print_result(result, compact: bool = False) -> None:
    if compact:
        conf = f"{result.confidence:.3f}" if result.confidence is not None else "N/A"
        tag = "✓ AUTH" if result.authorised else "✗ DENY"
        print(f"[{tag}] faces={result.faces_detected}  conf={conf}  {result.status.name}  {result.message}")
    else:
        border = "═" * 50
        print(f"\n{border}")
        print(f"  Status      : {result.status.name}")
        print(f"  Authorised  : {result.authorised}")
        print(f"  Message     : {result.message}")
        print(f"  Faces found : {result.faces_detected}")
        if result.confidence is not None:
            print(f"  Confidence  : {result.confidence:.4f}")
        if result.face_location:
            fl = result.face_location
            print(f"  Face bbox   : top={fl.top} right={fl.right} bottom={fl.bottom} left={fl.left}")
        print(f"  Latency     : {result.latency_ms:.1f} ms")
        print(f"{border}\n")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        prog="face_auth",
        description="Authorised Face Recognition System",
    )
    parser.add_argument(
        "--reference-dir", default=None,
        help="Override reference image directory (env: FACE_AUTH_REFERENCE_DIR)",
    )
    parser.add_argument(
        "--tolerance", type=float, default=None,
        help="Face-distance tolerance (env: FACE_AUTH_TOLERANCE)",
    )
    parser.add_argument(
        "--model", choices=["hog", "cnn"], default=None,
        help="Detection model (env: FACE_AUTH_MODEL)",
    )
    parser.add_argument(
        "--log-level", default=None,
        help="Logging verbosity: DEBUG|INFO|WARNING|ERROR",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # image sub-command
    img_p = sub.add_parser("image", help="Verify a single image file")
    img_p.add_argument("--input", required=True, help="Path to image file")

    # batch sub-command
    bat_p = sub.add_parser("batch", help="Verify all images in a directory")
    bat_p.add_argument("--input-dir", required=True, help="Path to directory of images")

    # stream sub-command
    str_p = sub.add_parser("stream", help="Continuous verification from camera/RTSP")
    str_p.add_argument("--source", default="0", help="Camera index or RTSP URL")
    str_p.add_argument("--gui", action="store_true", help="Enable GUI mode")

    if len(sys.argv) == 1:
        # Default for VS Code debugger or run without args
        sys.argv.extend(["stream", "--source", "0", "--gui"])

    args = parser.parse_args()

    # Build config (env vars → defaults, then CLI overrides)
    cfg = EngineConfig()
    if args.reference_dir:
        cfg.reference_dir = Path(args.reference_dir)
    if args.tolerance is not None:
        cfg.tolerance = args.tolerance
    if args.model:
        cfg.detection_model = args.model
    if args.log_level:
        cfg.log_level = args.log_level

    _setup_logging(cfg.log_level)

    # Build engine & auditor
    engine = FaceAuthEngine(
        reference_dir=cfg.reference_dir,
        tolerance=cfg.tolerance,
        model=cfg.detection_model,
        upsample=cfg.upsample,
        min_face_area_ratio=cfg.min_face_area_ratio,
    )

    auditor = AuditLogger(
        log_dir=cfg.log_dir,
        actor_id=cfg.actor_id,
    )

    # Dispatch
    command_map = {
        "image": cmd_image,
        "batch": cmd_batch,
        "stream": cmd_stream,
    }

    handler = command_map[args.command]
    return handler(args, cfg, engine, auditor)


if __name__ == "__main__":
    sys.exit(main())
