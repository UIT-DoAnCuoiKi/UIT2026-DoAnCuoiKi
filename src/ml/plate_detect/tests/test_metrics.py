import time
import pytest
from plate_detect.eval.metrics import bootstrap_ci, measure_latency


def test_bootstrap_constant_collapses():
    mean, lo, hi = bootstrap_ci([0.9] * 50, n_boot=200, seed=0)
    assert mean == pytest.approx(0.9)
    assert lo == pytest.approx(0.9) and hi == pytest.approx(0.9)


def test_bootstrap_ci_orders():
    vals = [0.1, 0.2, 0.9, 0.95, 0.5, 0.6, 0.55, 0.4]
    mean, lo, hi = bootstrap_ci(vals, n_boot=500, seed=1)
    assert lo <= mean <= hi


def test_measure_latency_median():
    med = measure_latency(lambda x: time.sleep(0.01), None, warmup=2, runs=5)
    assert med == pytest.approx(0.01, abs=0.02)
