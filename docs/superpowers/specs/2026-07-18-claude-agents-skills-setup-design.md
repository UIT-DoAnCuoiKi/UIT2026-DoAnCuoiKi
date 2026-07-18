# Claude Code Agents & Skills Setup — Design

**Date:** 2026-07-18
**Project:** Smart Parking Management System using Computer Vision and Edge AI (UIT thesis, 15/07–23/09/2026)
**Students:** Nguyễn Minh Nhật (25410104), Lê Quang Hoài Đức (25410034)

## Goal

Set up a `.claude/` configuration (skills, one agent, CLAUDE.md) that supports the full thesis workflow: research, phase-by-phase process guidance, report writing, and project-specific coding assistance.

## Decisions

| Topic | Decision |
|---|---|
| Report toolchain | LaTeX, UIT thesis template (community template as starting point; supervisor's template can replace later), Vietnamese prose with English technical terms, IEEE citations |
| Code stack | ML: Python, YOLOv8/YOLO26, PaddleOCR/EasyOCR, OpenCV, ONNX. App: FastAPI + React + PostgreSQL. Edge target: Raspberry Pi 5 |
| Process guidance | Single phase-aware mentor skill (not per-phase commands) |
| Research scope | Academic literature review + practical tech research + dataset research |
| Agent granularity | Domain knowledge in skills; only one subagent (research-agent) where context isolation pays |
| Architecture | Thin project skills that reuse installed global skills (`academic-research-writer`, `latex-formatting`, `architecture-diagrams`, `jupyter-notebook`, `data-analysis-jupyter`); project skills carry only project-specific knowledge |

## Repository Layout

```
UIT2026-DoAnCuoiKi/
├── CLAUDE.md                      # stack, conventions, phase table, global-skill deps
├── .claude/
│   ├── skills/
│   │   ├── project-mentor/SKILL.md
│   │   ├── research-assistant/SKILL.md
│   │   ├── thesis-writer/SKILL.md
│   │   ├── ml-training/SKILL.md
│   │   ├── colab-training/SKILL.md
│   │   ├── alpr-pipeline/SKILL.md
│   │   ├── backend-dashboard/SKILL.md
│   │   └── edge-deploy/SKILL.md
│   └── agents/
│       └── research-agent.md
├── report/                        # LaTeX thesis (UIT template, Vietnamese)
├── research/                      # research notes + BibTeX output
├── src/                           # code: ml/, backend/, frontend/, edge/
└── docs/
```

`report/`, `research/`, `src/` created as stubs (`.gitkeep` + short README each) so skills reference real paths.

## Skills

### project-mentor
- **Trigger:** "what's next", phase questions, stuck decisions, progress checks.
- **Contains:** full 10-week plan table (dates, tasks, owner Nhật/Đức, deliverables per week from the approved outline); ML-project best practices per phase — data versioning, experiment tracking (CSV log default, W&B optional), train/val/test discipline, evaluation protocol matching outline metrics (mAP@0.5, mAP@0.5:0.95, precision/recall, plate-level accuracy + CER, F1 + confusion matrix, color accuracy, end-to-end latency < 2 s/vehicle on Raspberry Pi 5).
- **Behavior:** reads current date and repo state, locates current phase, advises next steps, flags slipping deliverables, reminds the chapter-per-phase report rule. Cross-checks dates against the outline table rather than hardcoding "current week".

### research-assistant
- **Trigger:** "research X", "find papers", "find datasets", framework comparisons.
- **Covers:** (1) academic literature review — delegates citation rigor to global `academic-research-writer`, outputs structured notes plus IEEE BibTeX to `research/`; (2) practical tech research — YOLOv8 vs YOLO26, PaddleOCR vs EasyOCR, quantization options, deployment guides; (3) dataset research — public Vietnamese license-plate/vehicle datasets, licenses, labeling tools.
- **Domain anchors:** ALPR pipeline literature, Vietnamese plate specification (1-row car / 2-row motorbike, white/yellow/blue/red background classes).

### thesis-writer
- **Trigger:** "write chapter", any report work.
- **Contains:** UIT template conventions; Vietnamese academic prose with English technical terms kept untranslated; IEEE citations via BibTeX; chapter map tied to phases (Tổng quan → Dữ liệu → per-module chapters → Tích hợp → Triển khai biên → Đánh giá → Kết luận); LaTeX Vietnamese setup (XeLaTeX + fontspec, or pdfLaTeX + vietnam babel); figures produced via global `architecture-diagrams` skill.
- **Reuses:** global `academic-research-writer` and `latex-formatting`.

### ml-training
- **Trigger:** training/evaluation code.
- **Contains:** ultralytics YOLOv8 workflow, dataset YAML format, augmentation for plates, ResNet/MobileNet fine-tuning for vehicle classification, metric scripts matching outline metrics, ONNX export.

### colab-training
- **Trigger:** Colab notebook work, GPU training sessions.
- **Contains:** notebook structure for Colab (Drive mount, dataset staging, checkpoint autosave to Drive, resume after disconnect); repo ↔ Colab sync via in-notebook `git clone`; pinned installs (ultralytics, paddleocr); exporting trained weights back to `src/ml/weights/`; run tracking (CSV default, W&B optional).
- **Split of responsibility:** `ml-training` owns training logic; `colab-training` owns the Colab environment. Uses global `jupyter-notebook` for scaffolding.

### alpr-pipeline
- **Trigger:** detection → OCR → color integration code.
- **Contains:** plate crop + skew correction; 2-row plate line-splitting before OCR; Vietnamese plate regex/format validation; HSV color classification with CLAHE lighting normalization; per-frame pipeline API design (one vehicle in → plate string, vehicle type, plate color, evidence image out).

### backend-dashboard
- **Trigger:** API/DB/UI code.
- **Contains:** FastAPI project conventions; PostgreSQL schema (vehicles, in/out sessions, evidence images, fees); anti-fraud in/out plate matching logic; fee calculation rules; React dashboard pages (realtime in/out feed, in-lot lookup, statistics by vehicle type / plate color / traffic / revenue); personal-data-law constraints (access control, encryption of sensitive fields, automatic retention-based deletion after vehicle exit).

### edge-deploy
- **Trigger:** Raspberry Pi / optimization work.
- **Contains:** ONNX Runtime on ARM; INT8 quantization with before/after accuracy re-check; benchmark scripts (inference time per model and end-to-end, FPS, model size, memory, optional power W and FPS/W); PC-vs-edge comparison table format; Raspberry Pi 5 camera setup; systemd service packaging.

## Agent

### research-agent (`.claude/agents/research-agent.md`)
- Preloads `research-assistant` skill.
- Tools: WebSearch, WebFetch, Read, Write.
- Purpose: long multi-source research runs isolated from main context; writes findings + BibTeX to `research/`, returns a summary. Main thread handles small lookups inline and dispatches this agent for large literature sweeps.

## CLAUDE.md

Contents: project one-liner; stack; repo layout; condensed 10-week phase table; team split (Nhật: model training/OCR/classification/optimization; Đức: plate color/lighting, DB + in-out logic, dashboard, edge deployment); report rules (LaTeX, Vietnamese, IEEE, chapter-per-phase); skill index (when to use which); global-skill dependency note (academic-research-writer, latex-formatting, architecture-diagrams, jupyter-notebook — teammate must install same plugins); data-privacy constraints per Vietnamese Personal Data Protection Law (effective 01/01/2026).

## Verification

- Smoke-test each skill with a representative prompt after creation (e.g. `project-mentor` → "what's next?" must cite the correct current week; `thesis-writer` → produces a compilable Vietnamese LaTeX snippet).
- Test one `research-agent` dispatch on a small query end-to-end (notes + BibTeX land in `research/`).
- Author all SKILL.md files following the `writing-skills` skill.

## Error Handling

Skills are documentation, not runtime — the failure mode is stale content. Mitigations: `project-mentor` derives current phase from the date and outline table at invocation time; stack facts live once in CLAUDE.md and skills reference it rather than restating.

## Resolved Defaults

1. UIT LaTeX template: start from a community UIT thesis template; replace with supervisor-provided template if one appears.
2. Experiment tracking: simple CSV log + Drive checkpoints by default; W&B as optional upgrade.
