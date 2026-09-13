# Source code

- `ml/`: training, evaluation and export scripts; trained weights in `ml/weights/` (git-ignored if large). Raspberry Pi 5 benchmark scripts also live here: `run_pi_benchmark.sh`, `pi_power_monitor.py`, `summarize_pi_benchmark.py`.
- `backend/`: FastAPI app, PostgreSQL models (SQLite also works, used on the Pi).
- `frontend/`: React dashboard.
- `edge/`: edge worker that captures from a camera, runs inference and posts results to the backend, with a Containerfile and tests. Not deployed yet. The Pi 5 currently runs the backend and portal directly instead.
