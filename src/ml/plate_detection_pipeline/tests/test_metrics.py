from plate_detect.eval.metrics import bootstrap_ci, measure_latency, model_stats

def test_bootstrap_ci_orders_and_brackets_mean():
    mean, lo, hi = bootstrap_ci([0.90, 0.91, 0.89, 0.92, 0.88], n_boot=500, seed=0)
    assert lo <= mean <= hi
    assert abs(mean - 0.90) < 0.01

def test_measure_latency_returns_positive_median():
    calls = {"n": 0}
    def fn(_):
        calls["n"] += 1
    t = measure_latency(fn, None, warmup=2, runs=5)
    assert t >= 0.0 and calls["n"] == 7        # warmup + runs

def test_model_stats_reads_size_and_calls_yolo(tmp_path, monkeypatch):
    w = tmp_path / "m.pt"; w.write_bytes(b"0" * 2_000_000)   # ~2 MB
    class FakeModel:
        def info(self, verbose=False):
            return (100, 3_000_000, 0, 8.1)                  # layers, params, grads, GFLOPs
    monkeypatch.setattr("plate_detect.eval.metrics._load_yolo", lambda p: FakeModel())
    s = model_stats(str(w))
    assert round(s["params_M"], 1) == 3.0
    assert round(s["flops_G"], 1) == 8.1
    assert round(s["size_MB"], 1) == 2.0
