# Claude Code Agents & Skills Setup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create the `.claude/` configuration (8 project skills, 1 research agent, CLAUDE.md) plus repo scaffold supporting the smart-parking thesis workflow.

**Architecture:** Thin project skills carrying only project-specific knowledge; generic work delegates to installed global skills (`academic-research-writer`, `latex-formatting`, `architecture-diagrams`, `jupyter-notebook`). One subagent (`research-agent`) for context-isolated literature sweeps. CLAUDE.md is the single source of truth for stack facts; skills reference it rather than restating.

**Tech Stack:** Markdown skill files (Claude Code SKILL.md format), Claude Code agent definition format. Project domain: Python/YOLOv8/PaddleOCR/OpenCV/ONNX, FastAPI + React + PostgreSQL, Raspberry Pi 5, LaTeX (XeLaTeX, Vietnamese).

## Global Constraints

- Skill files live at `.claude/skills/<name>/SKILL.md` with YAML frontmatter containing `name` and `description` (description states when to invoke).
- Agent files live at `.claude/agents/<name>.md` with YAML frontmatter `name`, `description`, `tools`, `skills`.
- Report: LaTeX, Vietnamese prose with English technical terms kept untranslated, IEEE citations.
- Code stack facts (verbatim from spec): ML: Python, YOLOv8/YOLO26, PaddleOCR/EasyOCR, OpenCV, ONNX. App: FastAPI + React + PostgreSQL. Edge target: Raspberry Pi 5. Latency target: end-to-end < 2 s/vehicle on Raspberry Pi 5. Plate accuracy target: > 90% in standard conditions.
- Thesis timeline: 15/07/2026 – 23/09/2026, 10 weeks. Team: Nhật (25410104) — model training/OCR/classification/optimization; Đức (25410034) — plate color/lighting, DB + in-out logic, dashboard, edge deployment.
- Commits: conventional style, one commit per task, message ends with `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.
- Verification for skill files (no runtime tests exist): `sed -n` frontmatter check confirming `name:` and `description:` lines exist, plus file-tree check. Final task smoke-tests skills by invocation.

---

### Task 1: Repo scaffold (report/, research/, src/ stubs)

**Files:**
- Create: `report/README.md`
- Create: `research/README.md`
- Create: `src/README.md`
- Create: `report/.gitkeep`, `research/.gitkeep`, `src/.gitkeep`

**Interfaces:**
- Produces: directory paths `report/`, `research/`, `src/ml/weights/` (referenced by skills in Tasks 2–10). Skills MUST use these exact paths.

- [ ] **Step 1: Create directories and README stubs**

`report/README.md`:
```markdown
# Report — Báo cáo đồ án

LaTeX thesis (UIT template, tiếng Việt, IEEE citations). Built with XeLaTeX.

- Written stage-by-stage: each project phase ends with its corresponding chapter drafted here.
- Use the `thesis-writer` project skill for all report work.
```

`research/README.md`:
```markdown
# Research notes

Output directory for the `research-assistant` skill and `research-agent` subagent.

- One markdown file per research topic: `YYYY-MM-DD-<topic>.md`
- BibTeX entries collected in `refs.bib` (merged into report/ bibliography later).
```

`src/README.md`:
```markdown
# Source code

- `ml/` — training, evaluation, export scripts; trained weights in `ml/weights/` (git-ignored if large)
- `backend/` — FastAPI app + PostgreSQL models
- `frontend/` — React dashboard
- `edge/` — Raspberry Pi 5 deployment: optimized models, benchmark scripts, systemd packaging
```

```bash
mkdir -p report research src
touch report/.gitkeep research/.gitkeep src/.gitkeep
```

- [ ] **Step 2: Verify structure**

Run: `ls report research src`
Expected: each directory exists containing `README.md` and `.gitkeep`.

- [ ] **Step 3: Commit**

```bash
git add report research src
git commit -m "chore: scaffold report, research, and src directories

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 2: CLAUDE.md

**Files:**
- Create: `CLAUDE.md`

**Interfaces:**
- Consumes: directory paths from Task 1.
- Produces: single source of truth for stack facts + skill index. Skills in Tasks 3–10 reference "see CLAUDE.md" for stack facts instead of restating them.

- [ ] **Step 1: Write CLAUDE.md**

```markdown
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
- `colab-training` — Colab notebook environment, checkpoints, weight export
- `alpr-pipeline` — detection→OCR→color integration code
- `backend-dashboard` — FastAPI/PostgreSQL/React code
- `edge-deploy` — ONNX Runtime on Pi, quantization, benchmarks

## Global skill dependencies

Project skills delegate to these installed plugins (teammates: install the same): `academic-research-writer`, `latex-formatting`, `architecture-diagrams`, `jupyter-notebook`, `data-analysis-jupyter`.

## Data privacy (Luật Bảo vệ dữ liệu cá nhân, effective 01/01/2026)

License plates and vehicle images are personal data: access control on stored records, encrypt sensitive fields, auto-delete records after the regulated retention period following vehicle exit. Any code touching stored plate data must respect this.
```

- [ ] **Step 2: Verify**

Run: `head -5 CLAUDE.md`
Expected: title line present.

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: add CLAUDE.md with stack, phase plan, and skill index

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 3: project-mentor skill

**Files:**
- Create: `.claude/skills/project-mentor/SKILL.md`

**Interfaces:**
- Consumes: CLAUDE.md phase table (Task 2).
- Produces: skill name `project-mentor` (referenced in CLAUDE.md skill index).

- [ ] **Step 1: Write SKILL.md**

```markdown
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
4. Always check the report rule: has the previous phase's chapter been drafted in `report/`? If not, flag it first — báo cáo song hành is a graded requirement.

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

- **Data:** fixed train/val/test split committed as file lists; never evaluate on training data; version dataset changes (date-stamped snapshot notes in `research/`).
- **Experiments:** every training run logged — CSV (`src/ml/experiments.csv`: date, model, dataset version, hyperparams, metrics, weights path) by default, W&B optional. No untracked "best model".
- **Checkpoints:** weights saved to Drive during Colab runs (see `colab-training`), exported to `src/ml/weights/`.
- **Integration:** freeze module interfaces before week 6 (see `alpr-pipeline`).
- **Evaluation:** measure quantization accuracy drop explicitly — the accuracy/speed trade-off is a required thesis result, not a nuisance.

## Common stuck-points

- Behind schedule → cut scope per outline priorities: motorbike+car classes first, bus/truck eval is explicitly out of deep scope; free-flow is out of scope entirely.
- Model underperforms → check data first (label quality, class balance, lighting variety) before architecture changes.
- Integration pain in week 6 → almost always interface mismatch; re-read `alpr-pipeline` contract.
```

- [ ] **Step 2: Verify frontmatter**

Run: `sed -n '1,5p' .claude/skills/project-mentor/SKILL.md`
Expected: `---`, `name: project-mentor`, `description: ...` present.

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/project-mentor
git commit -m "feat: add project-mentor skill with 10-week phase guidance

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 4: research-assistant skill

**Files:**
- Create: `.claude/skills/research-assistant/SKILL.md`

**Interfaces:**
- Consumes: `research/` directory (Task 1).
- Produces: skill name `research-assistant`; note-file convention `research/YYYY-MM-DD-<topic>.md` + `research/refs.bib` (consumed by `research-agent` in Task 5 and `thesis-writer` in Task 6).

- [ ] **Step 1: Write SKILL.md**

```markdown
---
name: research-assistant
description: Use when researching papers, comparing frameworks/models (YOLO versions, OCR engines, quantization), or finding Vietnamese license-plate/vehicle datasets for the smart parking thesis. Produces structured notes and IEEE BibTeX in research/.
---

# Research Assistant

Three research modes for the smart parking thesis. All outputs land in `research/`:
- Notes: `research/YYYY-MM-DD-<topic>.md`
- Citations: append IEEE-style BibTeX entries to `research/refs.bib` (deduplicate by citation key)

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
```

- [ ] **Step 2: Verify frontmatter**

Run: `sed -n '1,5p' .claude/skills/research-assistant/SKILL.md`
Expected: `---`, `name: research-assistant`, `description:` present.

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/research-assistant
git commit -m "feat: add research-assistant skill for literature, tech, and dataset research

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 5: research-agent subagent

**Files:**
- Create: `.claude/agents/research-agent.md`

**Interfaces:**
- Consumes: `research-assistant` skill name (Task 4), `research/` conventions.
- Produces: agent name `research-agent` (dispatched from main thread for large sweeps).

- [ ] **Step 1: Write agent definition**

```markdown
---
name: research-agent
description: Dispatched for long multi-source research sweeps (literature reviews, dataset surveys, framework comparisons) for the smart parking thesis, keeping heavy web content out of the main context. Writes notes and BibTeX to research/ and returns a summary.
tools: WebSearch, WebFetch, Read, Write, Glob, Grep
skills: research-assistant
---

You are a research subagent for the UIT smart parking thesis (computer vision ALPR + edge AI). Follow the preloaded `research-assistant` skill for modes, note format, and output conventions.

Rules:
- Write full findings to `research/YYYY-MM-DD-<topic>.md` and append BibTeX to `research/refs.bib` — the main thread will NOT see your intermediate work, only your final summary.
- Your final message must contain: topic, number of sources reviewed, key findings (3–6 bullets), file paths written, and any open questions.
- Verify claims against primary sources (official docs, papers), not blog summaries.
- If the task is ambiguous, pick the interpretation most useful for the thesis chapter it feeds and state the assumption in your summary.
```

- [ ] **Step 2: Verify frontmatter**

Run: `sed -n '1,7p' .claude/agents/research-agent.md`
Expected: frontmatter with `name: research-agent`, `tools:`, `skills: research-assistant`.

- [ ] **Step 3: Commit**

```bash
git add .claude/agents/research-agent.md
git commit -m "feat: add research-agent subagent for isolated research sweeps

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 6: thesis-writer skill

**Files:**
- Create: `.claude/skills/thesis-writer/SKILL.md`

**Interfaces:**
- Consumes: `research/refs.bib` convention (Task 4), `report/` directory (Task 1).
- Produces: skill name `thesis-writer`; report structure `report/main.tex` + `report/chapters/`.

- [ ] **Step 1: Write SKILL.md**

```markdown
---
name: thesis-writer
description: Use for all thesis report work — writing chapters, LaTeX setup, citations, figures — for the smart parking thesis. Vietnamese academic prose, UIT template, IEEE citations, XeLaTeX.
---

# Thesis Writer

All report work happens in `report/`. Delegate LaTeX mechanics to global `latex-formatting`, citation rigor to `academic-research-writer`, and diagrams to `architecture-diagrams` (Mermaid/PlantUML exported to PDF/PNG for inclusion).

## Language rules

- Vietnamese academic prose (văn phong học thuật), third person, no first-person singular.
- English technical terms kept untranslated where standard: mAP, quantization, inference, OCR, bounding box, dataset, precision/recall, F1, FPS. Vietnamese term first with English in parentheses on first use: "lượng tử hóa (quantization)".
- Numbers + units: SI, comma as decimal separator in Vietnamese convention only in prose; keep `siunitx` defaults in tables.

## LaTeX setup

- Engine: **XeLaTeX** (required for Vietnamese via fontspec). Build: `latexmk -xelatex main.tex` run inside `report/`.
- Structure: `report/main.tex` includes `report/chapters/<nn>-<slug>.tex`, one file per chapter.
- Bibliography: `biblatex` with `style=ieee`, backend biber; source file `report/refs.bib` — sync entries from `research/refs.bib` (copy needed entries over; `research/refs.bib` is the superset).
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

1. Read the relevant `research/` notes and experiment results (`src/ml/experiments.csv`).
2. Outline the chapter (sections, figures, tables) — confirm with the user before prose.
3. Draft in Vietnamese; every claim from literature cites a `refs.bib` key; every number traces to an experiment log or benchmark output.
4. Compile (`latexmk -xelatex`) and fix warnings before presenting.

## Quality bar

- No uncited related-work claims; no metrics without source runs; figures referenced in prose (`Hình~\ref{...}`); tables use `booktabs`.
```

- [ ] **Step 2: Verify frontmatter**

Run: `sed -n '1,5p' .claude/skills/thesis-writer/SKILL.md`
Expected: `name: thesis-writer`, `description:` present.

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/thesis-writer
git commit -m "feat: add thesis-writer skill for Vietnamese UIT LaTeX report

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 7: ml-training skill

**Files:**
- Create: `.claude/skills/ml-training/SKILL.md`

**Interfaces:**
- Consumes: experiment log convention `src/ml/experiments.csv` (named in Task 3), weights path `src/ml/weights/`.
- Produces: skill name `ml-training`; dataset config convention `src/ml/data/<dataset>.yaml`.

- [ ] **Step 1: Write SKILL.md**

```markdown
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
```

- [ ] **Step 2: Verify frontmatter**

Run: `sed -n '1,5p' .claude/skills/ml-training/SKILL.md`
Expected: `name: ml-training`, `description:` present.

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/ml-training
git commit -m "feat: add ml-training skill for detection, classification, and OCR

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 8: colab-training skill

**Files:**
- Create: `.claude/skills/colab-training/SKILL.md`

**Interfaces:**
- Consumes: `ml-training` conventions (experiments.csv, weights path, dataset yaml).
- Produces: skill name `colab-training`; notebook location convention `src/ml/notebooks/`.

- [ ] **Step 1: Write SKILL.md**

```markdown
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
```

- [ ] **Step 2: Verify frontmatter**

Run: `sed -n '1,5p' .claude/skills/colab-training/SKILL.md`
Expected: `name: colab-training`, `description:` present.

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/colab-training
git commit -m "feat: add colab-training skill for GPU notebook workflow

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 9: alpr-pipeline skill

**Files:**
- Create: `.claude/skills/alpr-pipeline/SKILL.md`

**Interfaces:**
- Consumes: model conventions from `ml-training` (ONNX exports in `src/ml/weights/`).
- Produces: skill name `alpr-pipeline`; pipeline API contract `process_vehicle(image) -> VehicleRecord` consumed by `backend-dashboard` (Task 10) and `edge-deploy` (Task 11).

- [ ] **Step 1: Write SKILL.md**

```markdown
---
name: alpr-pipeline
description: Use when writing the recognition pipeline code — plate detection crops, skew correction, 2-row splitting, OCR integration, HSV plate-color classification, and the unified per-vehicle API — for the smart parking thesis.
---

# ALPR Pipeline

Integration code lives in `src/ml/pipeline/`. Consumes ONNX models from `src/ml/weights/`. This is the interface frozen before week-6 integration — changes after that need both students' agreement.

## Pipeline contract (the one API everything consumes)

```python
@dataclass
class VehicleRecord:
    plate_text: str          # normalized, e.g. "59A-123.45"; "" if unreadable
    plate_confidence: float  # min of detection and OCR confidence, 0..1
    vehicle_type: str        # "car" | "motorbike" | "truck" | "bus"
    plate_color: str         # "white" | "yellow" | "blue" | "red"
    evidence_jpeg: bytes     # full-scene image at capture time
    timestamp: datetime

def process_vehicle(image: np.ndarray) -> VehicleRecord: ...
```

One call per vehicle at the gate (stationary vehicle per scope — no tracking needed).

## Stage order

1. Vehicle + plate detection (YOLO ONNX) → largest-confidence vehicle box, plate box within it
2. Plate crop → skew correction: minAreaRect on plate contour, rotate to horizontal (cv2.warpAffine)
3. Row split: plate aspect ratio < ~2.0 ⇒ 2-row (motorbike) — split at horizontal projection-profile valley, OCR each row, join top+bottom
4. OCR (PaddleOCR) per row → concatenate
5. Format validation + normalization (below); on failure keep raw text, flag low confidence
6. Plate color: HSV classification on plate crop; CLAHE (on L channel of LAB) before HSV thresholds to handle lighting
7. Vehicle type: classifier on vehicle crop

## VN plate normalization

- Charset: A–Z (no I, O in series), 0–9. Common OCR confusions to correct by position: 0↔O, 1↔I, 8↔B, 5↔S, 2↔Z.
- Patterns (validate after uppercase + strip separators):
  - Car (1-row): `^\d{2}[A-Z]\d{4,5}$` (e.g. 51A12345)
  - Motorbike (2-row): `^\d{2}[A-Z]\d{1}\d{4,5}$` (row1: province+series, row2: number)
- Render normalized as `NNX-NNN.NN` (5-digit) or `NNX-NNNN` (4-digit) for display/storage.

## HSV color classes (starting thresholds — calibrate on own data, log final values for thesis)

- white: S < 40, V > 120 · yellow: H 20–35 · blue: H 95–130 · red: H < 10 or H > 160 (two ranges)
- Decide by majority of plate-crop pixels after CLAHE; record per-class accuracy per lighting condition.

## Testing

- Unit tests per stage with fixture images in `src/ml/pipeline/tests/fixtures/` (one clear + one hard case per: 1-row, 2-row, each color, low light).
- End-to-end test asserts full VehicleRecord on fixtures; latency measured here is the number `edge-deploy` benchmarks against.
```

- [ ] **Step 2: Verify frontmatter**

Run: `sed -n '1,5p' .claude/skills/alpr-pipeline/SKILL.md`
Expected: `name: alpr-pipeline`, `description:` present.

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/alpr-pipeline
git commit -m "feat: add alpr-pipeline skill with frozen VehicleRecord contract

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 10: backend-dashboard skill

**Files:**
- Create: `.claude/skills/backend-dashboard/SKILL.md`

**Interfaces:**
- Consumes: `VehicleRecord` contract from `alpr-pipeline` (Task 9).
- Produces: skill name `backend-dashboard`; DB schema + API route conventions.

- [ ] **Step 1: Write SKILL.md**

```markdown
---
name: backend-dashboard
description: Use when writing backend (FastAPI + PostgreSQL) or dashboard (React) code — in/out sessions, anti-fraud matching, fees, statistics — for the smart parking thesis.
---

# Backend & Dashboard

Backend in `src/backend/` (FastAPI + SQLAlchemy + PostgreSQL), dashboard in `src/frontend/` (React + Vite). Consumes `VehicleRecord` from `alpr-pipeline`.

## Database schema (PostgreSQL)

- `parking_sessions`: id, plate_text, plate_color, vehicle_type, entry_time, exit_time (nullable), entry_image_path, exit_image_path (nullable), entry_confidence, exit_confidence, fee_amount (nullable), status (`in_lot` | `completed` | `disputed`)
- `fee_rules`: id, vehicle_type, price_per_block, block_hours, active
- `users`: id, username, password_hash (bcrypt), role (`operator` | `admin`)
- Evidence images on disk `src/backend/storage/evidence/YYYY-MM-DD/<session-id>-{entry,exit}.jpg`; DB stores paths. **Privacy (CLAUDE.md):** plate_text encrypted at rest (pgcrypto `pgp_sym_encrypt` or app-level Fernet — pick one, document in report), role-based access on all read endpoints, nightly job deletes sessions + images past retention period after exit.

## In/out flow + anti-fraud

- **Entry:** `POST /api/sessions/entry` body = VehicleRecord fields → creates `in_lot` session, stores evidence image.
- **Exit:** `POST /api/sessions/exit` → find `in_lot` session with matching normalized plate. Match rules: exact match ⇒ compute fee, close. No match or vehicle_type mismatch ⇒ status `disputed`, operator resolves comparing entry/exit evidence images (this is the anti-fraud mechanism from the outline).
- Fee: ceil((exit − entry)/block_hours) × price_per_block by vehicle_type from active `fee_rules`.

## API routes

- `POST /api/sessions/entry`, `POST /api/sessions/exit` — called by pipeline host
- `GET /api/sessions?status=in_lot&plate=...` — lookup/search
- `GET /api/stats/traffic?granularity=hour|day` · `GET /api/stats/revenue` · `GET /api/stats/breakdown?by=vehicle_type|plate_color`
- `GET /api/sessions/{id}/evidence/{entry|exit}` — auth-gated image serve
- Auth: JWT bearer; `operator` reads + resolves disputes, `admin` also edits fee_rules and users.

## Dashboard pages (React)

1. **Live** — realtime in/out feed (poll 2 s or SSE), current in-lot count
2. **Lookup** — search by plate fragment; session detail with evidence images side-by-side
3. **Disputes** — `disputed` queue, operator resolve UI
4. **Stats** — charts: traffic over time, revenue, breakdown by vehicle type and plate color (recharts)
5. **Settings** (admin) — fee rules, users

## Conventions

- Pydantic schemas mirror DB models; SQLAlchemy 2.0 style; Alembic migrations from day one.
- Tests: pytest + httpx against a dockerized Postgres (or SQLite fallback marked xfail for pg-specific features); fee and matching logic get exhaustive unit tests — they're the anti-fraud thesis claims.
```

- [ ] **Step 2: Verify frontmatter**

Run: `sed -n '1,5p' .claude/skills/backend-dashboard/SKILL.md`
Expected: `name: backend-dashboard`, `description:` present.

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/backend-dashboard
git commit -m "feat: add backend-dashboard skill with schema and API conventions

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 11: edge-deploy skill

**Files:**
- Create: `.claude/skills/edge-deploy/SKILL.md`

**Interfaces:**
- Consumes: ONNX exports (`ml-training`), `process_vehicle` contract (`alpr-pipeline`), backend API (`backend-dashboard`).
- Produces: skill name `edge-deploy`; benchmark table format used in thesis chapter 07/08.

- [ ] **Step 1: Write SKILL.md**

```markdown
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
- Pi setup script `src/edge/setup.sh`: apt deps, venv, pinned pip installs (match Colab pins where shared), model download from Drive/release artifact.
- Backend may run on the Pi itself (Postgres via docker) or on LAN PC — both supported via env config; document which was used for each benchmark row.
```

- [ ] **Step 2: Verify frontmatter**

Run: `sed -n '1,5p' .claude/skills/edge-deploy/SKILL.md`
Expected: `name: edge-deploy`, `description:` present.

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/edge-deploy
git commit -m "feat: add edge-deploy skill for Pi 5 deployment and benchmarking

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 12: Smoke tests + final verification

**Files:**
- Modify: none (verification only; fixes applied to any file failing checks)

**Interfaces:**
- Consumes: everything from Tasks 1–11.

- [ ] **Step 1: Structural check**

Run:
```bash
for f in project-mentor research-assistant thesis-writer ml-training colab-training alpr-pipeline backend-dashboard edge-deploy; do
  test -f ".claude/skills/$f/SKILL.md" && grep -q "^name: $f$" ".claude/skills/$f/SKILL.md" && grep -q "^description: " ".claude/skills/$f/SKILL.md" && echo "OK $f" || echo "FAIL $f"
done
test -f .claude/agents/research-agent.md && echo "OK agent" || echo "FAIL agent"
```
Expected: 8× `OK <skill>` + `OK agent`. Fix any FAIL before continuing.

- [ ] **Step 2: Cross-reference check**

Run: `grep -l "VehicleRecord" .claude/skills/*/SKILL.md`
Expected: `alpr-pipeline` and `backend-dashboard` both listed (contract consistency).

Run: `grep -l "experiments.csv" .claude/skills/*/SKILL.md`
Expected: `project-mentor`, `ml-training`, `colab-training` listed.

- [ ] **Step 3: Invocation smoke test (requires interactive session — executor reports, user confirms)**

In a fresh Claude Code session in this repo, run each and verify sensible output:
1. Ask "what's next for the project?" → `project-mentor` invoked, cites correct current week from date.
2. Ask "compare PaddleOCR and EasyOCR briefly" → `research-assistant` invoked, offers note in `research/`.
3. Ask "set up the report skeleton" → `thesis-writer` invoked, proposes `report/main.tex` + chapters with XeLaTeX.

If a skill fails to auto-invoke, sharpen its frontmatter `description` (add trigger phrases) and re-test.

- [ ] **Step 4: Commit any fixes**

```bash
git add -A .claude CLAUDE.md
git commit -m "fix: adjust skill descriptions after smoke testing

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```
(Skip commit if no fixes were needed.)
