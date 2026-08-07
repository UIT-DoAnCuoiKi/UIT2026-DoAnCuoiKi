from __future__ import annotations
from ..config import Config
from .registry import resolve


def run_name(model_key: str, seed: int) -> str:
    return f"{model_key}_s{seed}"


def build_train_args(cfg: Config, data_yaml: str, seed: int, project: str, name: str) -> dict:
    """Return the Ultralytics train() kwargs (fixed for a fair comparison; includes A1-tuned augmentation presets)."""
    return {
        "data": data_yaml,
        "imgsz": cfg.imgsz,
        "epochs": cfg.epochs,
        "batch": cfg.batch,          # fixed for reproducible fair comparison
        "patience": cfg.patience,
        "seed": seed,
        "deterministic": True,
        "hsv_v": 0.5,                # brightness aug (~11% dark images in A1)
        "hsv_s": 0.7,
        "degrees": 5.0,              # mild skew (gate camera)
        "perspective": 0.0005,
        "close_mosaic": 10,
        "project": project,
        "name": name,
        "exist_ok": True,
        "verbose": False,
    }


def run_train(model_key: str, cfg: Config, data_yaml: str, seed: int, project: str) -> str:
    from ultralytics import YOLO
    model = YOLO(resolve(model_key))
    name = run_name(model_key, seed)
    results = model.train(**build_train_args(cfg, data_yaml, seed, project, name))
    return str(results.save_dir)

