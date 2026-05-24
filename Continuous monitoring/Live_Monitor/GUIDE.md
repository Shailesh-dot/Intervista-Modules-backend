# Device Detector — Quick Guide

## Setup
```bash
pip install -r requirements.txt
```

## Run instantly (no training needed)
```bash
python detect.py
```
Detects phones & laptops out of the box via COCO pretrained weights.
Tablet detection is weak here — fine-tune to fix it.

---

## Fine-tune for better tablet detection

1. Collect images → label with [LabelImg](https://github.com/HumanSignal/labelImg) in YOLO format
2. Arrange folders:
```
data/
  images/train/   ← your images
  images/val/
  labels/train/   ← .txt label files
  labels/val/
```
3. Run:
```bash
python finetune.py
```

## Production (fastest CPU)
```bash
python detect_onnx.py
```

---

## Files
| File | Purpose |
|---|---|
| `detect.py` | Quick start, no training |
| `finetune.py` | Train + export ONNX |
| `detect_onnx.py` | Production inference |
| `dataset.yaml` | Dataset config template |
