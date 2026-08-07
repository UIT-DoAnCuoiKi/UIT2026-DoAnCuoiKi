# src/ml/plate_detect/tests/test_pipeline_smoke.py
import os
import cv2
import pytest
from plate_detect.config import Config
from plate_detect.data.fixtures import make_raw_fixture
from plate_detect.data.prepare import prepare

pytestmark = pytest.mark.slow

def test_full_pipeline_cpu(tmp_path):
    # 1. fixtures → prepare
    raw = tmp_path / "raw"; make_raw_fixture(str(raw), n_per_split=8, seed=0)
    cfg = Config(
        raw_dir=str(raw), processed_dir=str(tmp_path / "proc"),
        dataset_yaml=str(tmp_path / "a1_det.yaml"), split_dir=str(tmp_path / "split"),
        imgsz=64, epochs=1, batch=2,
    )
    summary = prepare(cfg)
    assert summary["counts"]["train"] == 8

    # 2. train 1 epoch on CPU (downloads yolov8n.pt on first run)
    from plate_detect.train.trainer import run_train
    run_dir = run_train("yolov8n", cfg, cfg.dataset_yaml, seed=0,
                        project=str(tmp_path / "runs"))
    best = os.path.join(run_dir, "weights", "best.pt")
    assert os.path.exists(best)

    # 3. inference via PlateDetector (pt backend)
    from plate_detect.inference.plate_detector import PlateDetector
    det = PlateDetector(best, backend="pt", conf=0.01)
    val_imgs = sorted((tmp_path / "proc" / "images" / "val").glob("*.jpg"))
    assert val_imgs, "prepare() produced no val images — check split logic"
    img = cv2.imread(val_imgs[0].as_posix())
    assert img is not None, f"cv2.imread returned None for {val_imgs[0]}"
    dets = det.detect(img)           # may be empty on a 1-epoch model; must not crash
    assert isinstance(dets, list)

    # 4. export ONNX
    from plate_detect.export.to_onnx import export
    onnx_path = export(best, str(tmp_path / "model.onnx"), imgsz=64)
    assert os.path.exists(onnx_path)
