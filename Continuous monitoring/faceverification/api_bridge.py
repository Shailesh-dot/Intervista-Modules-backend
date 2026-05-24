import cv2
import threading
import uvicorn
import time
import shutil
from fastapi import FastAPI, BackgroundTasks, File, UploadFile
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

from config import EngineConfig
from face_engine import FaceAuthEngine
from stream_verifier import StreamVerifier
from audit_logger import AuditLogger

app = FastAPI(title="Bridge API for Continuous Monitoring")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global State
cfg = EngineConfig()
engine = None
auditor = None
verifier = None
lock = threading.Lock()

def on_result(result):
    if auditor:
        auditor.log(result, source="0")

def init_monitoring():
    global engine, auditor, verifier
    with lock:
        if verifier is None:
            print("[BRIDGE] Initializing FaceAuthEngine...")
            engine = FaceAuthEngine(
                reference_dir=cfg.reference_dir, 
                tolerance=cfg.tolerance, 
                model=cfg.detection_model
            )
            auditor = AuditLogger(log_dir=cfg.log_dir)
            verifier = StreamVerifier(
                engine=engine,
                source=0,
                fps_cap=cfg.stream_fps_cap,
                on_result=on_result
            )
            verifier.start()
            print("[BRIDGE] Engine Started and Camera Locked!")

@app.post("/start")
def start_monitoring(background_tasks: BackgroundTasks):
    background_tasks.add_task(init_monitoring)
    return {"status": "starting"}

@app.get("/status")
def get_status():
    if not verifier:
        return {"status": "loading", "message": "Monitoring not started", "faces_detected": 0}
    res = verifier.latest_result
    if res:
        return {
            "status": res.status.name, 
            "message": res.message, 
            "authorised": res.authorised,
            "faces_detected": res.faces_detected
        }
    return {"status": "loading", "message": "Waiting for frame", "faces_detected": 0}

def generate_frames():
    while not verifier:
        time.sleep(0.1)
    
    while True:
        with lock:
            if verifier is None:
                break
            frame = verifier.latest_frame
            
        if frame is not None:
            # We stream the raw frame back to the browser
            ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 50])
            if ret:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
        else:
            time.sleep(0.01)

@app.post("/reset")
def reset_proctoring():
    global verifier, engine
    with lock:
        if verifier is not None:
            verifier.stop()
            verifier = None
        engine = None
    return {"status": "ok"}

@app.post("/reference")
def set_reference(file: UploadFile = File(...)):
    # 1. Clear existing reference images
    if cfg.reference_dir.exists():
        for p in cfg.reference_dir.iterdir():
            if p.is_file():
                p.unlink()
    else:
        cfg.reference_dir.mkdir(parents=True, exist_ok=True)
        
    # 2. Save new reference
    new_path = cfg.reference_dir / "reference.jpg"
    with open(new_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    # 3. Reset verifier so it re-initializes with the new reference on next start
    global verifier, engine
    with lock:
        if verifier is not None:
            verifier.stop()
            verifier = None
        engine = None
        
    print(f"[BRIDGE] Reference saved to {new_path}")
    return {"status": "success"}

@app.get("/video_feed")
def video_feed():
    return StreamingResponse(generate_frames(), media_type="multipart/x-mixed-replace; boundary=frame")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8004)
