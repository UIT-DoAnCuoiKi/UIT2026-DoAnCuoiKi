from __future__ import annotations
import os
import csv
import datetime
import statistics

_HEADER = ["date", "model", "dataset", "hyperparams",
           "mAP50", "mAP50-95", "precision", "recall", "weights"]


def aggregate_seeds(runs: list[dict]) -> dict[str, tuple[float, float]]:
    """Aggregate per-seed metrics into mean and population std.

    Args:
        runs: List of metric dicts with keys like map50, map5095, precision, recall.

    Returns:
        Dict mapping metric key to (mean, std) tuple.
    """
    if not runs:
        return {}
    out = {}
    for k in runs[0].keys():
        vals = [r[k] for r in runs]
        # population std: a single seed yields 0.0 (pstdev handles len==1 natively)
        out[k] = (statistics.mean(vals), statistics.pstdev(vals))
    return out


def append_experiment(csv_path: str, model: str, dataset: str,
                      hyperparams: str, m: dict, weights: str) -> None:
    """Append aggregated metrics to experiments CSV ledger.

    Creates header if file does not exist. Formats metric values to 4 decimals.

    Args:
        csv_path: Path to experiments.csv
        model: Model identifier (e.g., 'yolo26n')
        dataset: Dataset name (e.g., 'A1')
        hyperparams: Hyperparameters string (e.g., 'imgsz=640;epochs=100')
        m: Dict with keys 'map50', 'map5095', 'precision', 'recall'
        weights: Path to model weights file
    """
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
