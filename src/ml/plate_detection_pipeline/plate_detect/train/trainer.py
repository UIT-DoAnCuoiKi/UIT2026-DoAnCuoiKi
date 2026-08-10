from __future__ import annotations
import os
from ..config import Config
from .registry import resolve


def run_name(model_key: str, seed: int, imgsz: int) -> str:
    return f"{model_key}_s{seed}_{imgsz}"


def build_train_args(cfg: Config, data_yaml: str, seed: int,
                     project: str, name: str, imgsz: int) -> dict:
    """Ultralytics train() kwargs — fixed across both models for a fair comparison;
    A1-tuned augmentation (mild brightness for ~8% dark images, mild skew for gate camera)."""
    return {
        "data": data_yaml,
        "imgsz": imgsz,
        "epochs": cfg.epochs,
        "batch": cfg.batch,
        "patience": cfg.patience,
        "seed": seed,
        "deterministic": True,
        "hsv_v": 0.5,
        "hsv_s": 0.7,
        "degrees": 5.0,
        "perspective": 0.0005,
        "close_mosaic": 10,
        # Absolute project path so Ultralytics' get_save_dir does NOT prepend
        # RUNS_DIR/<task>/ (which turns "runs" into "runs/detect/runs/<name>").
        # Absolute => save_dir = <project>/<name>, matching how eval/export reconstruct it.
        "project": os.path.abspath(project),
        "name": name,
        "exist_ok": True,
        "verbose": False,
    }


def run_train(model_key: str, cfg: Config, data_yaml: str, seed: int,
              project: str, imgsz: int | None = None) -> str:
    from ultralytics import YOLO
    imgsz = cfg.imgsz if imgsz is None else imgsz
    name = run_name(model_key, seed, imgsz)
    model = YOLO(resolve(model_key))
    results = model.train(**build_train_args(cfg, data_yaml, seed, project, name, imgsz))
    return str(results.save_dir)
