---
name: colab-training
description: Use when creating or editing Google Colab notebooks for GPU training — Drive mounting, checkpointing, session-loss recovery, syncing code and weights with the repo — for the smart parking thesis.
---

# Colab Training

Owns the Colab *environment*; `ml-training` owns the training logic. Notebooks live in `src/ml/notebooks/`, committed to git (scaffold with global `jupyter-notebook` skill). Assume sessions die without warning — every notebook must be resumable.

## Standard notebook structure (in order)

1. **Setup cell:** pinned installs — `pip install ultralytics==<pinned> paddleocr==<pinned>` (pin exact versions in the notebook the first time they're chosen; never floating).
2. **Drive mount:** `from google.colab import drive; drive.mount('/content/drive')`. Project Drive root: `/content/drive/MyDrive/UIT2026-DoAnCuoiKi/` with `datasets/`, `checkpoints/`, `weights/`.
3. **Repo clone cell:** `git clone https://github.com/<org>/UIT2026-DoAnCuoiKi.git` (shallow), so notebook uses repo dataset YAMLs and scripts — no code copy-paste into cells.
4. **Dataset staging:** copy zipped dataset from Drive to local `/content/` and unzip (Drive-direct reads are slow); verify file counts against split lists.
5. **Training cell:** call training per `ml-training` skill, with `project=/content/drive/MyDrive/UIT2026-DoAnCuoiKi/checkpoints/<run-name>` so ultralytics checkpoints land on Drive every epoch.
6. **Resume cell:** `yolo detect train resume model=<drive checkpoint>/last.pt` — the cell to run after a disconnect.
7. **Export + handoff cell:** export ONNX, copy `best.pt` + `.onnx` to Drive `weights/`, print final metrics row to append to `src/ml/experiments.csv`.

## Rules

- One notebook per experiment family (`detect-yolov8.ipynb`, `classify-resnet-mobilenet.ipynb`, `ocr-eval.ipynb`), parametrized by a config cell at top — not one notebook per run.
- After a run: metrics row goes into `src/ml/experiments.csv` in the repo (committed), weights recorded by Drive path; small final ONNX may be copied into `src/ml/weights/`.
- Notebook outputs cleared before commit (`jupyter nbconvert --clear-output`) — keep diffs readable.
- Colab free tier disconnects ~90 min idle: long trainings need checkpoint-every-epoch (step 5 handles this) and the resume cell tested before relying on it.
