import cv2
from ultralytics import YOLO

# COCO class IDs we care about
TARGET = {63: "Laptop", 67: "Phone", 76: "Tablet"}

model = YOLO("yolov8n.pt")  # downloads automatically on first run

cap = cv2.VideoCapture(0)  # 0 = default webcam
if not cap.isOpened():
    raise RuntimeError("Cannot open camera")

print("Press Q to quit")

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

        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(frame, label, (x1, y1 - 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

    cv2.imshow("Device Detector", frame)
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()
