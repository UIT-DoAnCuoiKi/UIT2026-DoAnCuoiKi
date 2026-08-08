import os
from plate_detect.eval.evaluate import aggregate_seeds, append_experiment, comparison_table

def test_aggregate_seeds_mean_and_std():
    runs = [{"map50": 0.90, "map5095": 0.60}, {"map50": 0.92, "map5095": 0.62}]
    agg = aggregate_seeds(runs)
    assert abs(agg["map50"][0] - 0.91) < 1e-9
    assert agg["map50"][1] > 0.0

def test_append_experiment_writes_header_then_row(tmp_path):
    csv = tmp_path / "experiments.csv"
    m = {"map50": 0.9123, "map5095": 0.6001, "precision": 0.9, "recall": 0.88}
    append_experiment(str(csv), "yolo26n", "A1", "imgsz=640", m, "weights/yolo26n.pt")
    lines = open(csv).read().splitlines()
    assert lines[0].startswith("date,model,dataset,hyperparams")
    assert "yolo26n" in lines[1] and "0.9123" in lines[1]

def test_comparison_table_has_headers_and_ci():
    rows = [{
        "model": "yolo26n", "imgsz": 640, "map50_mean": 0.98, "map50_std": 0.004,
        "map5095_mean": 0.71, "map5095_ci": (0.69, 0.73), "precision": 0.95,
        "recall": 0.93, "params_M": 3.0, "flops_G": 8.1, "size_MB": 6.2,
        "lat_model_ms": 12.0, "lat_e2e_ms": 13.0, "fps": 76.9,
    }]
    md = comparison_table(rows)
    assert "| model | imgsz |" in md
    assert "yolo26n" in md and "0.69" in md and "0.73" in md
