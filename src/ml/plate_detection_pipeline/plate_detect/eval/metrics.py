from __future__ import annotations
import os
import time
import numpy as np


def bootstrap_ci(values, n_boot: int = 1000, seed: int = 0, alpha: float = 0.05):
    arr = np.asarray(values, dtype=float)
    rng = np.random.default_rng(seed)
    n = len(arr)
    boot = np.array([arr[rng.integers(0, n, n)].mean() for _ in range(n_boot)])
    lo, hi = np.percentile(boot, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return float(arr.mean()), float(lo), float(hi)


def measure_latency(fn, inp, warmup: int = 5, runs: int = 20) -> float:
    for _ in range(warmup):
        fn(inp)
    times = []
    for _ in range(runs):
        t0 = time.perf_counter()
        fn(inp)
        times.append(time.perf_counter() - t0)
    return float(np.median(times))


def _load_yolo(weights_pt: str):
    from ultralytics import YOLO
    return YOLO(weights_pt)


def model_stats(weights_pt: str) -> dict:
    """Hardware-independent primaries: params (M), FLOPs (G), file size (MB)."""
    m = _load_yolo(weights_pt)
    info = m.info(verbose=False)      # (layers, params, gradients, gflops)
    params = float(info[1]) if info else 0.0
    flops = float(info[3]) if info and len(info) > 3 else 0.0
    return {
        "params_M": params / 1e6,
        "flops_G": flops,
        "size_MB": os.path.getsize(weights_pt) / 1e6,
    }
