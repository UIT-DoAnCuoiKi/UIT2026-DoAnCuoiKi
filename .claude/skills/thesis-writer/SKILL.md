---
name: thesis-writer
description: Use for all thesis report work — writing chapters, LaTeX setup, citations, figures — for the smart parking thesis. Vietnamese academic prose, UIT template, IEEE citations, XeLaTeX.
---

# Thesis Writer

All report work happens in `docs/report/`. Delegate LaTeX mechanics to global `latex-formatting`, citation rigor to `academic-research-writer`, and diagrams to `architecture-diagrams` (Mermaid/PlantUML exported to PDF/PNG for inclusion).

Draft each chapter as Markdown first (`docs/report/chapters/<nn>-<slug>.md`) — faster to iterate and review. Only build/update the `.tex` version when explicitly asked to formalize/typeset, or when a milestone genuinely needs the PDF (e.g. submitting to the advisor). See `docs/report/README.md`.

## Language rules

- Vietnamese academic prose (văn phong học thuật), third person, no first-person singular.
- English technical terms kept untranslated where standard: mAP, quantization, inference, OCR, bounding box, dataset, precision/recall, F1, FPS. Vietnamese term first with English in parentheses on first use: "lượng tử hóa (quantization)".
- Numbers + units: SI. Configure `siunitx` with `output-decimal-marker={,}` so tables match Vietnamese comma-decimal prose convention.

## LaTeX setup

- Engine: **XeLaTeX** (required for Vietnamese via fontspec). Build: `latexmk -xelatex main.tex` run inside `docs/report/`.
- Structure: `docs/report/main.tex` includes `docs/report/chapters/<nn>-<slug>.tex`, one file per chapter.
- Bibliography: `biblatex` with `style=ieee`, backend biber; source file `docs/report/refs.bib` — sync entries from `docs/research/refs.bib` (copy needed entries over; `docs/research/refs.bib` is the superset).
- Template: start from a community UIT thesis template; if the supervisor provides an official one, swap the preamble, keep chapter files.

## Chapter map (mirrors phases — write each at phase end)

1. `01-tongquan.tex` — Tổng quan: problem, related work/ALPR survey, objectives, scope (week 1)
2. `02-dulieu.tex` — Dữ liệu: sources, collection, labeling, splits (week 2)
3. `03-phathien.tex` — Phát hiện xe và biển số: YOLO training + results (week 3)
4. `04-ocr-maubien.tex` — OCR và màu biển: OCR pipeline, HSV color module (weeks 3–4)
5. `05-phanloai.tex` — Phân loại phương tiện: ResNet vs MobileNet (week 5)
6. `06-hethong.tex` — Hệ thống quản lý: DB, in/out logic, fees, dashboard (weeks 4–6)
7. `07-trienkhai.tex` — Triển khai thiết bị biên: ONNX, quantization, Pi deployment (weeks 7–8)
8. `08-danhgia.tex` — Đánh giá: full metrics, PC vs edge, lighting conditions (week 9)
9. `09-ketluan.tex` — Kết luận và hướng phát triển (week 10)

## Writing workflow per chapter

1. Read the relevant `docs/research/` notes and experiment results (`src/ml/experiments.csv`).
2. Outline the chapter (sections, figures, tables) — confirm with the user before prose.
3. Draft in Vietnamese; every claim from literature cites a `refs.bib` key; every number traces to an experiment log or benchmark output.
4. Compile (`latexmk -xelatex`) and fix warnings before presenting.

## Quality bar

- No uncited related-work claims; no metrics without source runs; figures referenced in prose (`Hình~\ref{...}`); tables use `booktabs`.
