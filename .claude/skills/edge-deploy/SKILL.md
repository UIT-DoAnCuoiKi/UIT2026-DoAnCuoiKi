---
name: edge-deploy
description: Use when working on Raspberry Pi 5 deployment — ONNX Runtime on ARM, INT8 quantization, benchmarking, camera capture, service packaging — for the smart parking thesis.
---

# Edge Deploy

Deployment code in `src/edge/`. Target: Raspberry Pi 5 (8 GB), 64-bit Raspberry Pi OS. Goal from outline: end-to-end < 2 s/vehicle; PC-vs-edge comparison is a required thesis result.

## Runtime

- `onnxruntime` (CPU ExecutionProvider, ARM64 wheel) — same pipeline code as PC via `process_vehicle` from `alpr-pipeline`, only the model paths differ (quantized variants).
- Threads: set `intra_op_num_threads=4` (Pi 5 = 4×Cortex-A76); measure before/after, don't assume.
- Camera: Pi Camera Module or USB webcam via OpenCV `VideoCapture`; capture triggered per vehicle (button/sensor stub or manual trigger for demo) — no continuous inference.

## Quantization

- Dynamic INT8 first (`onnxruntime.quantization.quantize_dynamic`) — no calibration set needed; static INT8 (with ~200-image calibration set) only if dynamic accuracy drop > 2 points.
- **Required measurement:** every metric re-run after quantization on the same test set; report FP32 vs INT8 delta per model. Accuracy/speed trade-off is a thesis result, not a footnote.

## Benchmark protocol (thesis table format)

One row per (model, platform, precision):

| Model | Platform | Precision | Size (MB) | Inference (ms) | E2E (ms) | FPS | RAM (MB) | Accuracy metric |

- Inference time: median of 100 runs after 10 warmup runs; E2E = full `process_vehicle` on fixture set.
- RAM: peak RSS via `psutil` around inference loop.
- Optional power: USB power meter → W and FPS/W columns.
- Platforms: dev PC (record CPU/GPU spec) and Pi 5; identical fixture set and code revision — record git SHA in the results file `src/edge/benchmarks/results.csv`.

## Packaging

- systemd unit `parking-edge.service`: runs capture→pipeline→POST to backend loop; `Restart=on-failure`; env file for backend URL + model paths.
- Pi setup script `src/edge/setup.sh`: apt deps, venv, pinned pip installs (match training-env pins where shared), model download from release artifact.
- Backend may run on the Pi itself (Postgres via docker) or on LAN PC — both supported via env config; document which was used for each benchmark row.
