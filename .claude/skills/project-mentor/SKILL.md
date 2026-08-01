---
name: project-mentor
description: Use when the user asks "what's next", where the project stands, how to approach a phase, or is stuck on a process/planning decision for the smart parking thesis. Phase-aware mentor knowing the full 10-week plan and ML-project best practices.
---

# Project Mentor

Phase-aware guide for the smart parking thesis (15/07/2026 – 23/09/2026). Stack + condensed plan: see CLAUDE.md. Full outline: `docs/DCDATN_*.docx` (converted text) / README.md.

## How to answer "what's next"

1. Get today's date. Locate current week in the plan table below (derive from dates — never assume).
2. Check repo state against that week's deliverable (does the module/chapter exist? committed?).
3. Report: current phase, what should be done by now, what's missing, concrete next steps for each student (Nhật/Đức).
4. Always check the report rule: has the previous phase's chapter been drafted in `docs/report/`? If not, flag it first — báo cáo song hành is a graded requirement.

## Full 10-week plan

| Week | Dates | Phase | Nhật | Đức | Deliverable |
|---|---|---|---|---|---|
| 1 | 15/07–22/07 | Overview research + env setup | Deep-dive systems/edge deployment | Deep-dive model training | Approved outline; environments ready; overview chapter |
| 2 | 22/07–29/07 | Data | Both: download public VN datasets, photograph parking lots in varied lighting, label, split train/val/test | (shared) | Labeled dataset; data chapter |
| 3 | 29/07–05/08 | Parallel | Train vehicle+plate detector, skew correction | HSV plate-color module + CLAHE lighting | Detector meets mAP; color module works |
| 4 | 05/08–12/08 | Parallel | OCR train/integrate, 1-row + 2-row plates | DB schema, in/out logic, plate matching, fees | Plate strings read; DB + logic work |
| 5 | 12/08–19/08 | Parallel | Vehicle classifier, ResNet vs MobileNet, F1 | Dashboard (type/color/traffic/revenue stats) | Classifier + metrics; dashboard works |
| 6 | 19/08–26/08 | Integration | Both: merge detection+OCR+classification+color into one pipeline, connect DB + dashboard | (shared) | End-to-end on PC |
| 7 | 26/08–02/09 | Parallel | ONNX export + quantization | Pi setup, system packaging | Optimized models; Pi ready |
| 8 | 02/09–09/09 | Edge deploy | Both: deploy to Pi, per-vehicle processing, fix integration bugs | (shared) | Runs on Raspberry Pi 5 |
| 9 | 09/09–16/09 | Evaluation | Both: measure all metrics PC vs edge across lighting conditions | (shared) | Full metrics + comparison tables |
| 10 | 16/09–23/09 | Finalize | Both: assemble report, slides, demo video | (shared) | Complete deliverables |

## Evaluation protocol (from approved outline — use these, no substitutes)

- Detection (vehicle, plate): mAP@0.5, mAP@0.5:0.95, precision, recall
- OCR: plate-level accuracy + character-level accuracy (CER)
- Vehicle classification: accuracy, F1, confusion matrix
- Plate color: accuracy
- All tested across multiple lighting conditions
- Edge: inference time (per-model and end-to-end), FPS, model size, memory, accuracy before/after quantization, optional power (W, FPS/W); PC vs edge comparison
- Targets: plate reading > 90% standard conditions; < 2 s/vehicle end-to-end on Raspberry Pi 5

## ML best practices to enforce

- **Data:** fixed train/val/test split committed as file lists; never evaluate on training data; version dataset changes (date-stamped snapshot notes in `docs/research/`).
- **Experiments:** every training run logged — CSV (`src/ml/experiments.csv`: date, model, dataset version, hyperparams, metrics, weights path) by default, W&B optional. No untracked "best model".
- **Checkpoints:** weights saved to Drive during Colab runs (see `colab-training`), exported to `src/ml/weights/`.
- **Integration:** freeze module interfaces before week 6 (see `alpr-pipeline`).
- **Evaluation:** measure quantization accuracy drop explicitly — the accuracy/speed trade-off is a required thesis result, not a nuisance.

## Common stuck-points

- Behind schedule → cut scope per outline priorities: motorbike+car classes first, bus/truck eval is explicitly out of deep scope; free-flow is out of scope entirely.
- Model underperforms → check data first (label quality, class balance, lighting variety) before architecture changes.
- Integration pain in week 6 → almost always interface mismatch; re-read `alpr-pipeline` contract.
