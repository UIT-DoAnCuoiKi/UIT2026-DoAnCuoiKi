from __future__ import annotations
import time
import numpy as np


def bootstrap_ci(
    values: list[float],
    n_boot: int = 1000,
    seed: int = 0,
    alpha: float = 0.05,
) -> tuple[float, float, float]:
    """
    Compute bootstrap confidence interval for the mean of values.

    Args:
        values: List of float values to analyze.
        n_boot: Number of bootstrap resamples (default 1000).
        seed: Random seed for reproducibility (default 0).
        alpha: Significance level for confidence interval (default 0.05).

    Returns:
        Tuple of (mean, lo, hi) where mean is the sample mean and
        [lo, hi] is the confidence interval.
    """
    arr = np.asarray(values, dtype=float)
    rng = np.random.default_rng(seed)
    n = len(arr)
    boot = np.array([arr[rng.integers(0, n, n)].mean() for _ in range(n_boot)])
    lo, hi = np.percentile(boot, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return float(arr.mean()), float(lo), float(hi)


def measure_latency(fn, inp, warmup: int = 5, runs: int = 20) -> float:
    """
    Measure median latency of a function call.

    Args:
        fn: Callable to measure.
        inp: Input argument to pass to fn.
        warmup: Number of warmup calls before timing (default 5).
        runs: Number of timed runs (default 20).

    Returns:
        Median elapsed time in seconds.
    """
    for _ in range(warmup):
        fn(inp)
    times = []
    for _ in range(runs):
        t0 = time.perf_counter()
        fn(inp)
        times.append(time.perf_counter() - t0)
    return float(np.median(times))
