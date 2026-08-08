import os
import plate_detect.cli as C
from plate_detect.config import Config
from plate_detect.data.fixtures import make_raw_fixture

def _common(tmp_path):
    raw = tmp_path / "raw"; make_raw_fixture(str(raw), n_per_split=8, seed=0)
    return ["--raw-dir", str(raw), "--processed-dir", str(tmp_path / "proc"),
            "--dataset-yaml", str(tmp_path / "a1.yaml"), "--split-dir", str(tmp_path / "split")]

def test_dry_run_no_compute(capsys, tmp_path):
    rc = C.main(["prepare", "--dry-run"] + _common(tmp_path))
    assert rc == 0
    assert "[dry-run]" in capsys.readouterr().out
    assert not os.path.exists(tmp_path / "proc")     # nothing prepared

def test_prepare_then_check(tmp_path):
    common = _common(tmp_path)
    assert C.main(["prepare"] + common) == 0
    assert C.main(["check"] + common) == 0            # data-contract OK

def test_train_dispatches_per_model_and_seed(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(C, "run_train",
                        lambda mk, cfg, y, seed, project, imgsz=None: calls.append((mk, seed, imgsz)) or f"{project}/{mk}_s{seed}_{imgsz}")
    cfg = Config(dataset_yaml=str(tmp_path / "a1.yaml"))
    dirs = C.cmd_train(cfg, project=str(tmp_path / "runs"),
                       models=["yolov8n", "yolo26n"], imgsz=640, seeds=[0, 1])
    assert len(calls) == 4 and ("yolo26n", 1, 640) in calls
    assert len(dirs) == 4

def test_export_calls_export_and_parity(monkeypatch, tmp_path):
    monkeypatch.setattr(C, "export", lambda pt, out, imgsz=640: out)
    cfg = Config()
    out = C.cmd_export(cfg, weights_pt=str(tmp_path / "best.pt"),
                       out_onnx=str(tmp_path / "m.onnx"), imgsz=640)
    assert out.endswith("m.onnx")
