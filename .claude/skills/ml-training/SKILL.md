---
name: ml-training
description: Use when writing model training, evaluation, or export code — YOLO detection, ResNet/MobileNet classification, OCR fine-tuning — for the smart parking thesis.
---

# ML Training

Training/eval/export code lives in `src/ml/`. Environment: Google Colab GPU (see `colab-training` skill for environment; this skill owns the training logic). Log every run to `src/ml/experiments.csv` (date, model, dataset version, hyperparams, metrics, weights path).

## Detection (vehicle + plate) — ultralytics YOLOv8

- Dataset config: `src/ml/data/<dataset>.yaml` (ultralytics format: `path`, `train`, `val`, `test`, `names`). Two detectors or one multi-class model — start with one model, classes: `car, motorbike, truck, bus, plate`; split later only if plate recall suffers.
- Train: `yolo detect train data=... model=yolov8n.pt imgsz=640 epochs=100` — start from `n`/`s` sizes (edge target), scale up only with evidence.
- Augmentation: default mosaic + hsv augment; add small-rotation (±10°) — plates photographed at gate angles.
- Eval: `yolo detect val` → record mAP@0.5, mAP@0.5:0.95, precision, recall per class into experiments.csv.
- Export: `yolo export format=onnx opset=17 imgsz=640` (dynamic=False for edge predictability).

## Classification (vehicle type) — ResNet vs MobileNet

- torchvision fine-tune: ResNet18 and MobileNetV3-Small, pretrained ImageNet weights, replace final layer with 4 classes (car, motorbike, truck, bus).
- Same split file lists as detection crops; input 224×224; report accuracy, macro-F1, confusion matrix (deep eval only on car/motorbike per scope).
- Compare both in one table: accuracy, F1, params, ONNX size, CPU inference ms — the comparison itself is a thesis result.

## OCR

- Start with pretrained PaddleOCR recognition (en + digits covers VN plates: A–Z, 0–9, hyphen/dot). Fine-tune only if plate-level accuracy < 90% target on val set.
- 2-row plates: split lines before recognition (handled in `alpr-pipeline`); OCR receives single-line crops.
- Metrics: plate-level exact-match accuracy + CER; evaluate per lighting condition.

## Rules

- Fixed splits from committed file lists — never random-split at train time.
- Every reported thesis number must exist in experiments.csv with a weights path.
- Save nothing large to git: weights → Drive + `src/ml/weights/` (git-ignored beyond small final ONNX files).
