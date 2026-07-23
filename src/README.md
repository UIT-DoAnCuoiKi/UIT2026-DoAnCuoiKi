# Source code

- `ml/` — training, evaluation, export scripts; trained weights in `ml/weights/` (git-ignored if large)
- `backend/` — FastAPI app + PostgreSQL models
- `frontend/` — React dashboard
- `edge/` — Raspberry Pi 5 deployment: optimized models, benchmark scripts, systemd packaging
