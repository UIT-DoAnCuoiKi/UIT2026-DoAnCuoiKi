import pytest
from plate_detect.eval.evaluate import aggregate_seeds, append_experiment


def test_aggregate_mean_std():
    runs = [
        {"map50": 0.90, "map5095": 0.60, "precision": 0.9, "recall": 0.9},
        {"map50": 0.92, "map5095": 0.62, "precision": 0.9, "recall": 0.9},
        {"map50": 0.94, "map5095": 0.64, "precision": 0.9, "recall": 0.9},
    ]
    agg = aggregate_seeds(runs)
    assert agg["map50"][0] == pytest.approx(0.92)
    assert agg["map50"][1] == pytest.approx(0.0163, abs=1e-3)   # population-ish std


def test_append_experiment_schema(tmp_path):
    csv = tmp_path / "experiments.csv"
    m = {"map50": 0.93, "map5095": 0.63, "precision": 0.91, "recall": 0.9}
    append_experiment(str(csv), "yolo26n", "A1", "imgsz=640;epochs=100", m, "weights/x.pt")
    header, row = csv.read_text().splitlines()[:2]
    assert header == "date,model,dataset,hyperparams,mAP50,mAP50-95,precision,recall,weights"
    assert "yolo26n" in row and "A1" in row


def test_aggregate_single_seed():
    agg = aggregate_seeds([{"map50": 0.9, "map5095": 0.6, "precision": 0.9, "recall": 0.9}])
    assert agg["map50"] == (0.9, 0.0)   # population std of one value is 0.0


def test_aggregate_empty_returns_empty():
    assert aggregate_seeds([]) == {}


def test_append_twice_one_header_two_rows(tmp_path):
    csv = tmp_path / "experiments.csv"
    m = {"map50": 0.9, "map5095": 0.6, "precision": 0.9, "recall": 0.9}
    append_experiment(str(csv), "yolo26n", "A1", "h", m, "w1.pt")
    append_experiment(str(csv), "yolov8n", "A1", "h", m, "w2.pt")
    lines = csv.read_text().splitlines()
    assert lines[0] == "date,model,dataset,hyperparams,mAP50,mAP50-95,precision,recall,weights"
    assert len(lines) == 3   # one header + two data rows
