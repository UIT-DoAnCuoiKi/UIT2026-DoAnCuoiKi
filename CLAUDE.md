# CLAUDE.md

Smart Parking Management System using Computer Vision and Edge AI — UIT graduation thesis (đồ án tốt nghiệp), 15/07/2026 – 23/09/2026.

## Team

- **Nguyễn Minh Nhật (25410104):** vehicle/plate detection training, OCR, vehicle classification, model optimization (ONNX, quantization)
- **Lê Quang Hoài Đức (25410034):** plate color + lighting handling, database + in/out logic + fees, dashboard, edge deployment

## Stack

- **ML:** Python, YOLOv8/YOLO26 (ultralytics), PaddleOCR/EasyOCR, OpenCV (HSV, CLAHE), ONNX + quantization
- **App:** FastAPI backend, React dashboard, PostgreSQL
- **Edge target:** Raspberry Pi 5, end-to-end latency target < 2 s/vehicle
- **Training environment:** Google Colab GPU (see `colab-training` skill)
- **Report:** LaTeX (XeLaTeX), Vietnamese prose with English technical terms kept, IEEE citations

## Repo layout

- `report/` — LaTeX thesis, written chapter-per-phase
- `research/` — research notes + `refs.bib` (BibTeX)
- `src/ml/`, `src/backend/`, `src/frontend/`, `src/edge/` — code
- `docs/` — approved outline (đề cương) + specs/plans

## 10-week plan (condensed)

| Week | Dates | Phase | Deliverable |
|---|---|---|---|
| 1 | 15/07–22/07 | Literature study, env setup | Overview chapter |
| 2 | 22/07–29/07 | Data collection + labeling | Labeled dataset, data chapter |
| 3 | 29/07–05/08 | Detection (Nhật) ∥ plate color/HSV+CLAHE (Đức) | Detector meets mAP; color module works |
| 4 | 05/08–12/08 | OCR (Nhật) ∥ DB + in/out logic (Đức) | Plate strings read; DB + logic works |
| 5 | 12/08–19/08 | Classification (Nhật) ∥ dashboard (Đức) | Classifier + metrics; dashboard works |
| 6 | 19/08–26/08 | System integration | End-to-end on PC |
| 7 | 26/08–02/09 | Model optimization (Nhật) ∥ edge prep (Đức) | Optimized portable models; Pi ready |
| 8 | 02/09–09/09 | Edge deployment | System runs on Raspberry Pi 5 |
| 9 | 09/09–16/09 | Testing + multi-platform evaluation | Full metrics tables, PC-vs-edge comparison |
| 10 | 16/09–23/09 | Report finalization | Complete report, slides, demo video |

Report rule: every phase ends with its chapter drafted (viết song hành).

## Project skills (`.claude/skills/`)

- `project-mentor` — "what's next", phase guidance, progress checks
- `research-assistant` — papers, tech comparisons, dataset research (heavy sweeps → dispatch `research-agent`)
- `thesis-writer` — all report/LaTeX work
- `ml-training` — YOLO/ResNet/MobileNet training + eval code
- `colab-training` — Colab notebook environment (browser, VS Code extension, colab-mcp), checkpoints, weight export
- `alpr-pipeline` — detection→OCR→color integration code
- `backend-dashboard` — FastAPI/PostgreSQL/React code
- `edge-deploy` — ONNX Runtime on Pi, quantization, benchmarks

## Global skill dependencies

Project skills delegate to these installed plugins (teammates: install the same): `academic-research-writer`, `latex-formatting`, `architecture-diagrams`, `jupyter-notebook`, `data-analysis-jupyter`.

## Data privacy (Luật Bảo vệ dữ liệu cá nhân, effective 01/01/2026)

License plates and vehicle images are personal data: access control on stored records, encrypt sensitive fields, auto-delete records after the regulated retention period following vehicle exit. Any code touching stored plate data must respect this.
