from __future__ import annotations
import os
import csv
import datetime
import statistics

_HEADER = ["date", "model", "dataset", "hyperparams",
           "mAP50", "mAP50-95", "precision", "recall", "weights"]


def run_eval(weights_pt: str, data_yaml: str, imgsz: int,
             conf: float, iou: float) -> dict:
    from ultralytics import YOLO
    res = YOLO(weights_pt).val(data=data_yaml, split="test", imgsz=imgsz,
                               conf=conf, iou=iou, verbose=False)
    box = res.box
    return {
        "map50": float(box.map50),
        "map5095": float(box.map),
        "precision": float(box.mp),
        "recall": float(box.mr),
    }


def aggregate_seeds(runs: list[dict]) -> dict[str, tuple[float, float]]:
    if not runs:
        return {}
    out = {}
    for k in runs[0]:
        if isinstance(runs[0][k], (int, float)):
            vals = [r[k] for r in runs]
            out[k] = (statistics.mean(vals), statistics.pstdev(vals))
    return out


def append_experiment(csv_path: str, model: str, dataset: str,
                      hyperparams: str, m: dict, weights: str) -> None:
    exists = os.path.exists(csv_path)
    os.makedirs(os.path.dirname(csv_path) or ".", exist_ok=True)
    with open(csv_path, "a", newline="") as f:
        w = csv.writer(f)
        if not exists:
            w.writerow(_HEADER)
        w.writerow([
            datetime.date.today().isoformat(), model, dataset, hyperparams,
            f"{m['map50']:.4f}", f"{m['map5095']:.4f}",
            f"{m['precision']:.4f}", f"{m['recall']:.4f}", weights,
        ])


def comparison_table(rows: list[dict]) -> str:
    head = ("| model | imgsz | mAP@0.5 (mean±std) | mAP@0.5:0.95 [95% CI] | P | R "
            "| params(M) | FLOPs(G) | size(MB) | lat_model(ms) | lat_e2e(ms) | FPS |")
    sep = "|" + "---|" * 12
    lines = [head, sep]
    for r in rows:
        lo, hi = r["map5095_ci"]
        lines.append(
            f"| {r['model']} | {r['imgsz']} "
            f"| {r['map50_mean']:.4f}±{r['map50_std']:.4f} "
            f"| {r['map5095_mean']:.4f} [{lo:.2f}, {hi:.2f}] "
            f"| {r['precision']:.3f} | {r['recall']:.3f} "
            f"| {r['params_M']:.2f} | {r['flops_G']:.2f} | {r['size_MB']:.2f} "
            f"| {r['lat_model_ms']:.1f} | {r['lat_e2e_ms']:.1f} | {r['fps']:.1f} |"
        )
    return "\n".join(lines)
