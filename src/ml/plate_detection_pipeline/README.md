# plate_detect — A1 plate-detection pipeline

License-plate **detection** training/eval pipeline for the smart-parking thesis.
Compares **YOLO26n vs YOLOv8n** on the A1 dataset, with a 2-class layout head
(`bien_1hang` = single-row plate, `bien_2hang` = two-row plate).

All logic lives in the `plate_detect` package and is driven by a single CLI.
The training notebook (`notebooks/train-plate-det.ipynb`) is a thin driver that
only calls this CLI — it works on a local GPU kernel or on Colab.

## Install

```bash
# from this directory (src/ml/plate_detection_pipeline)
pip install -e .
# or from the repo root
pip install -e src/ml/plate_detection_pipeline
```

This puts the `plate_detect` console script on your PATH. Python ≥ 3.11.
Key deps: `ultralytics==8.4.37`, `opencv-python-headless`, `onnxruntime`.

> **Run every command from the repo root.** The CLI's default paths
> (`data/raw/...`, `data/processed/...`, `src/ml/plate_detect/configs/...`) are
> relative to the current working directory.

## Data layout

Raw A1 = Kaggle [`duydieunguyen/licenseplates`](https://www.kaggle.com/datasets/duydieunguyen/licenseplates),
placed at `data/raw/kaggle_vn_plate_segment/` with the layout the adapter reads:

```
data/raw/kaggle_vn_plate_segment/
  images/{train,val}/*.jpg
  labels/{train,val}/*.txt      # polygon labels: <cls> x1 y1 x2 y2 x3 y3 x4 y4
```

`prepare` writes the processed YOLO dataset to `data/processed/a1_det/`
(`images/{train,val,test}`, `labels/{train,val,test}`) and regenerates the
dataset yaml + split lists.

## Pipeline

Run in order. Model keys: `yolov8n`, `yolo26n` (both by default).

| Step | Command | Does |
|---|---|---|
| 1. Prepare | `plate_detect prepare` | class-map gate → re-split raw val into val+test (stratified) → pHash dedup report → write `data/processed/a1_det/` + dataset yaml |
| 2. Check | `plate_detect check` | validate the processed data contract (labels, class ids, splits) |
| 3. Train | `plate_detect train --imgsz 640 --seeds 0,1,2 --project runs` | train the model matrix → `runs/<model>_s<seed>_<imgsz>/weights/best.pt` |
| 3b. Ablation | `plate_detect train --imgsz 960 --seeds 0 --project runs` | imgsz ablation, single seed |
| 4. Export | `plate_detect export --weights runs/yolo26n_s0_640/weights/best.pt --out weights/yolo26n_a1_640.onnx --imgsz 640` | best.pt → ONNX, parity-checked. Name must be `weights/<model>_a1_<imgsz>.onnx` for eval to pick up latency |
| 5. Eval | `plate_detect eval --imgszs 640,960 --project runs --weights-dir weights --sample-image <test img>` | aggregate seeds → mAP + bootstrap CI + params/FLOPs/latency → comparison table + `experiments.csv` |

Example eval with an auto-picked sample image:

```bash
plate_detect eval --imgszs 640,960 --project runs --weights-dir weights \
  --sample-image data/processed/a1_det/images/test/$(ls data/processed/a1_det/images/test | head -1)
```

## Config & flags

Defaults live in `plate_detect/config.py`; override per run via flags or a YAML
passed with `--config`.

- `--imgsz` (train/export), `--imgszs 640,960` (eval, comma list)
- `--seeds 0,1,2` (default `[0,1,2]`)
- `--models yolov8n,yolo26n`
- `--project runs`, `--weights-dir weights`
- `--raw-dir`, `--processed-dir`, `--dataset-yaml`, `--split-dir`
- `--csv` (default `src/ml/experiments.csv`), `--table` (default `docs/report/figures/plate_det_comparison.md`)
- `--dry-run` prints the resolved config without running

## Outputs

- `data/processed/a1_det/` — processed dataset + `phash_report.txt` (near-dup report)
- `runs/<model>_s<seed>_<imgsz>/` — Ultralytics run dirs (`weights/best.pt`, curves)
- `weights/<model>_a1_<imgsz>.onnx` — exported models
- `src/ml/experiments.csv` — appended metrics per run
- `docs/report/figures/plate_det_comparison.md` — YOLO26n vs YOLOv8n table

## Colab

Open `notebooks/train-plate-det.ipynb` from the `feat/plate-detect-a1` branch and
run the **Setup** cell. It clones the branch (GitHub PAT), installs this package,
and unzips raw A1 from Google Drive (`MyDrive/UIT_2025/datasets/A1.zip`, mounted
and symlinked into the raw path — no per-session re-download). All later cells
call the CLI.

## Caveat — dedup leakage

Real A1 has **~40% train↔test near-duplicate frames**. `plate_detect prepare`
runs with `drop_dups=False` (writes the pHash report but keeps dups), so
**test mAP is optimistic**. For a real held-out eval, prepare with
`drop_dups=True` (currently only via `prepare(cfg, drop_dups=True)` in code — no
CLI flag yet). See `data/processed/a1_det/phash_report.txt` for the pair counts.

## Tests

```bash
pytest                 # unit tests (fast)
pytest -m slow         # end-to-end smoke test (trains a tiny model on CPU)
```
