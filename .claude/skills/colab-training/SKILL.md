---
name: colab-training
description: Use when creating or editing Google Colab notebooks for GPU training, connecting to Colab runtimes via the VS Code Colab extension or the colab-mcp MCP server — Drive mounting, checkpointing, session-loss recovery, syncing code and weights with the repo — for the smart parking thesis.
---

# Colab Training

Owns the Colab *environment*; `ml-training` owns the training logic. Notebooks live in `src/ml/notebooks/`, committed to git (scaffold with global `jupyter-notebook` skill). Assume sessions die without warning — every notebook must be resumable.

Three ways to reach a Colab GPU runtime — pick per situation:

1. **Browser Colab** — baseline workflow below; works from any machine.
2. **VS Code Colab extension** — edit repo notebooks locally, execute on a Colab GPU kernel; preferred for day-to-day training (see section below).
3. **colab-mcp** — Claude Code drives a live Colab runtime via the MCP server configured in `.mcp.json` (see section below).

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

## VS Code Colab extension

Connect a local VS Code notebook to a Colab GPU runtime: install Google's Colab extension, sign in with the Google account, open a repo notebook (`src/ml/notebooks/*.ipynb`), and pick the Colab runtime as the kernel.

Differences from the browser workflow:

- The notebook file lives in the local repo, not Drive — **skip the repo-clone cell (step 3)**; commit from local git as usual.
- Code executes on the *remote* runtime: `/content/` paths refer to Colab's filesystem, not the local disk. The runtime still needs the Drive-mount cell (step 2) and dataset-staging cell (step 4) — local repo files are not on the runtime, so dataset YAMLs/scripts the training needs must come from Drive or be small enough to inline in the config cell.
- Checkpointing to Drive (step 5) is unchanged and still mandatory: a VS Code disconnect only drops the local view, but the runtime itself can also die — Drive checkpoints + resume cell (step 6) remain the recovery path.
- Clear outputs before commit rule applies unchanged.

## colab-mcp (Claude-driven runtime)

`.mcp.json` configures the `colab-mcp` server (`uvx git+https://github.com/googlecolab/colab-mcp`). Entry point: the `mcp__colab-mcp__open_colab_browser_connection` tool opens a browser connection to a Colab notebook session; once connected, Claude can operate the notebook/runtime through the server's tools.

- Use for: starting/monitoring training cells and reading outputs/metrics from within a Claude Code session, without switching to the browser.
- Requires a signed-in Chrome/browser session with the target Colab notebook accessible.
- All standard rules still apply — checkpoints to Drive, metrics row appended to `src/ml/experiments.csv`, notebook committed with cleared outputs.
- Do not babysit long trainings by polling through MCP: checkpoint-every-epoch + the resume cell are the safety net, same as every other access path.
