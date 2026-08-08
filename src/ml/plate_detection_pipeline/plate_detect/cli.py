from __future__ import annotations
import argparse
import glob
import os
import sys
import cv2
from .config import Config
from .data.prepare import prepare
from .data.validate import validate_processed
from .train.registry import MODEL_REGISTRY
from .train.trainer import run_train, run_name
from .eval.evaluate import run_eval, aggregate_seeds, append_experiment, comparison_table
from .eval.metrics import bootstrap_ci, model_stats, measure_latency
from .export.to_onnx import export, parity_ok
from .inference.plate_detector import PlateDetector


def _cfg_from_args(a) -> Config:
    over = {}
    for k in ("raw_dir", "processed_dir", "dataset_yaml", "split_dir", "imgsz"):
        v = getattr(a, k, None)
        if v is not None:
            over[k] = v
    return Config.load(getattr(a, "config", None), **over)


def cmd_train(cfg: Config, project: str, models: list[str], imgsz: int,
              seeds: list[int]) -> list[str]:
    dirs = []
    for mk in models:
        for seed in seeds:
            dirs.append(run_train(mk, cfg, cfg.dataset_yaml, seed, project, imgsz=imgsz))
    return dirs


def _best_paths(project: str, model: str, imgsz: int, seeds: list[int]) -> list[str]:
    out = []
    for seed in seeds:
        p = os.path.join(project, run_name(model, seed, imgsz), "weights", "best.pt")
        if os.path.exists(p):
            out.append(p)
    return out


def _latency_onnx(onnx_path: str, image, names: dict, conf: float, iou: float):
    """Model-only (network forward) vs end-to-end (forward + decode/NMS) on ONNX."""
    import numpy as np
    import onnxruntime as ort
    det = PlateDetector(onnx_path, backend="onnx", names=names, conf=conf, iou=iou)
    det.detect(image)                       # warm the session
    sess = det._session
    iname = sess.get_inputs()[0].name
    h, w = sess.get_inputs()[0].shape[2:]
    h = h if isinstance(h, int) else 640
    w = w if isinstance(w, int) else 640
    blob = cv2.resize(image, (w, h))[:, :, ::-1].transpose(2, 0, 1)[None]
    blob = np.ascontiguousarray(blob, dtype=np.float32) / 255.0
    lat_model = measure_latency(lambda b: sess.run(None, {iname: b}), blob)
    lat_e2e = measure_latency(det.detect, image)
    fps = 1.0 / lat_e2e if lat_e2e > 0 else 0.0
    return lat_model * 1000.0, lat_e2e * 1000.0, fps


def cmd_eval(cfg: Config, project: str, models: list[str], imgszs: list[int],
             csv_path: str, table_path: str, weights_dir: str, sample_image: str) -> str:
    img = cv2.imread(sample_image) if sample_image and os.path.exists(sample_image) else None
    rows = []
    for mk in models:
        for imgsz in imgszs:
            bests = _best_paths(project, mk, imgsz, cfg.seeds)
            if not bests:
                continue
            per_seed = [run_eval(b, cfg.dataset_yaml, imgsz, cfg.conf, cfg.iou) for b in bests]
            agg = aggregate_seeds(per_seed)
            _, lo, hi = bootstrap_ci([r["map5095"] for r in per_seed])
            # TODO(optional): per-image bootstrap from saved preds (design 9.2, B~1000 over test images)
            best_pt = bests[0]
            stats = model_stats(best_pt)
            onnx_path = os.path.join(weights_dir, f"{mk}_a1_{imgsz}.onnx")
            if img is not None and os.path.exists(onnx_path):
                lat_model, lat_e2e, fps = _latency_onnx(onnx_path, img, cfg.class_names, cfg.conf, cfg.iou)
            else:
                lat_model = lat_e2e = fps = 0.0
            append_experiment(csv_path, mk, "A1",
                              f"imgsz={imgsz};epochs={cfg.epochs};seeds={cfg.seeds}",
                              {"map50": agg["map50"][0], "map5095": agg["map5095"][0],
                               "precision": agg["precision"][0], "recall": agg["recall"][0]},
                              best_pt)
            rows.append({
                "model": mk, "imgsz": imgsz,
                "map50_mean": agg["map50"][0], "map50_std": agg["map50"][1],
                "map5095_mean": agg["map5095"][0], "map5095_ci": (lo, hi),
                "precision": agg["precision"][0], "recall": agg["recall"][0],
                "params_M": stats["params_M"], "flops_G": stats["flops_G"],
                "size_MB": stats["size_MB"], "lat_model_ms": lat_model,
                "lat_e2e_ms": lat_e2e, "fps": fps,
            })
    md = comparison_table(rows)
    os.makedirs(os.path.dirname(table_path) or ".", exist_ok=True)
    with open(table_path, "w") as f:
        f.write(md + "\n")
    return md


def cmd_export(cfg: Config, weights_pt: str, out_onnx: str, imgsz: int) -> str:
    os.makedirs(os.path.dirname(out_onnx) or ".", exist_ok=True)
    export(weights_pt, out_onnx, imgsz=imgsz)
    return out_onnx


def _int_list(s: str) -> list[int]:
    return [int(x) for x in str(s).split(",") if str(x).strip() != ""]


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    p = argparse.ArgumentParser(
        prog="plate_detect",
        epilog="Global flags follow the subcommand, e.g. plate_detect train --imgsz 960 --seeds 0",
    )
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("prepare", "train", "eval", "export", "check"):
        sp = sub.add_parser(name)
        sp.add_argument("--config")
        sp.add_argument("--dry-run", action="store_true")
        sp.add_argument("--raw-dir", dest="raw_dir")
        sp.add_argument("--processed-dir", dest="processed_dir")
        sp.add_argument("--dataset-yaml", dest="dataset_yaml")
        sp.add_argument("--split-dir", dest="split_dir")
        sp.add_argument("--project", default="runs")
        sp.add_argument("--imgsz", type=int)
        sp.add_argument("--imgszs", default="640")            # eval: comma list
        sp.add_argument("--seeds")                            # comma list; default cfg.seeds
        sp.add_argument("--models", default=",".join(MODEL_REGISTRY))
        sp.add_argument("--weights")                          # export: best.pt
        sp.add_argument("--out")                              # export: out.onnx
        sp.add_argument("--weights-dir", dest="weights_dir", default="weights")
        sp.add_argument("--csv", default="src/ml/experiments.csv")
        sp.add_argument("--table", default="docs/report/figures/plate_det_comparison.md")
        sp.add_argument("--sample-image", dest="sample_image", default="")

    a = p.parse_args(argv)
    cfg = _cfg_from_args(a)
    models = [m for m in a.models.split(",") if m]
    seeds = _int_list(a.seeds) if a.seeds else cfg.seeds

    if a.dry_run:
        print(f"[dry-run] cmd={a.cmd} raw={cfg.raw_dir} processed={cfg.processed_dir} "
              f"models={models} seeds={seeds} imgsz={a.imgsz or cfg.imgsz}")
        return 0

    if a.cmd == "prepare":
        print(f"prepared: {prepare(cfg)}")
        return 0
    if a.cmd == "check":
        errs = validate_processed(cfg.processed_dir, cfg.num_classes)
        if errs:
            print("INVALID:\n  " + "\n  ".join(errs)); return 1
        print("data-contract OK"); return 0
    if a.cmd == "train":
        dirs = cmd_train(cfg, a.project, models, a.imgsz or cfg.imgsz, seeds)
        print("trained:\n  " + "\n  ".join(dirs)); return 0
    if a.cmd == "eval":
        md = cmd_eval(cfg, a.project, models, _int_list(a.imgszs),
                      a.csv, a.table, a.weights_dir, a.sample_image)
        print(md); return 0
    if a.cmd == "export":
        out = cmd_export(cfg, a.weights, a.out, a.imgsz or cfg.imgsz)
        print(f"exported: {out}"); return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
