"""
Fine-tune YOLOv8n to improve tablet detection.
Prepare your dataset in YOLO format first (see guide).
"""
from ultralytics import YOLO

model = YOLO("yolov8n.pt")

model.train(
    data="dataset.yaml",   # path to your dataset config
    epochs=50,
    imgsz=640,
    batch=8,               # safe for CPU RAM
    device="cpu",
    workers=2,
    project="runs/train",
    name="device_detector",
    patience=10,           # early stopping
)

# Export to ONNX for fastest CPU inference
model.export(format="onnx", dynamic=True, simplify=True)
print("Exported to ONNX — use detect_onnx.py for production")
