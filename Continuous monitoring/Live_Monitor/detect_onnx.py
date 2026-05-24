"""
Production inference using ONNX — fastest CPU speed.
Run finetune.py first to generate best.onnx
"""
from ultralytics import YOLO
import cv2

TARGET = {63: "Laptop", 67: "Phone", 76: "Tablet"}

model = YOLO("runs/train/device_detector/weights/best.onnx", task="detect")

cap = cv2.VideoCapture(0)
print("ONNX mode — Press Q to quit")

while True:
    ret, frame = cap.read()
    if not ret:
        break

    results = model(frame, verbose=False)[0]

    for box in results.boxes:
        cls = int(box.cls)
        if cls not in TARGET:
            continue
        conf = float(box.conf)
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        label = f"{TARGET[cls]} {conf:.2f}"
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 200, 255), 2)
        cv2.putText(frame, label, (x1, y1 - 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 200, 255), 2)

    cv2.imshow("Device Detector [ONNX]", frame)
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()
