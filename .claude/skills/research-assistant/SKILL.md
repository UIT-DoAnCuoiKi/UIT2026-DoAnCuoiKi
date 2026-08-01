---
name: research-assistant
description: Use when researching papers, comparing frameworks/models (YOLO versions, OCR engines, quantization), or finding Vietnamese license-plate/vehicle datasets for the smart parking thesis. Produces structured notes and IEEE BibTeX in docs/research/.
---

# Research Assistant

Three research modes for the smart parking thesis. All outputs land in `docs/research/`:
- Notes: `docs/research/YYYY-MM-DD-<topic>.md`
- Citations: append IEEE-style BibTeX entries to `docs/research/refs.bib` (deduplicate by citation key)

For large multi-source sweeps, dispatch the `research-agent` subagent instead of working inline — it preloads this skill.

## Mode 1: Academic literature review

For thesis Chapter Tổng quan. Invoke the global `academic-research-writer` skill for source-quality and citation rigor. Anchor topics:
- ALPR (automatic license plate recognition) pipeline surveys
- YOLO family: YOLOv8 architecture, YOLO26; single-stage detection
- Scene-text/OCR: PaddleOCR (PP-OCR), EasyOCR, CRNN/CTC background
- Edge AI: model compression, quantization (INT8), ONNX Runtime on ARM
- Vietnamese plate specifics: 1-row (car) vs 2-row (motorbike) layouts; background colors white (private), yellow (commercial), blue (government), red (military)

Note format per paper: full citation, 3–5 sentence summary, relevance to our system, BibTeX entry.

## Mode 2: Practical tech research

Decision-support comparisons. Always produce a comparison table + recommendation + risks. Standing questions:
- YOLOv8 vs YOLO26: accuracy/speed/export support on ARM
- PaddleOCR vs EasyOCR: Vietnamese plate character set, 2-row handling, ARM inference speed
- Quantization paths: ONNX Runtime static/dynamic INT8, accuracy impact
- Verify claims against official docs/release notes — model landscape moves fast; do not answer from memory.

## Mode 3: Dataset research

For each candidate dataset record: name, URL, size, classes, license (usable in a thesis?), plate types covered (VN 1-row/2-row?), lighting variety, annotation format. Known starting points to verify: Vietnamese plate datasets on Roboflow Universe, GreenParking, UIT-published vehicle datasets, Kaggle VN license plate sets. Labeling tools: Label Studio, CVAT, Roboflow annotate.

## Rules

- Every factual claim in notes gets a source link.
- BibTeX keys: `<firstauthor><year><keyword>` (e.g. `redmon2016yolo`).
- End every note with a "Feeds into" line naming the thesis chapter or module the finding affects.
