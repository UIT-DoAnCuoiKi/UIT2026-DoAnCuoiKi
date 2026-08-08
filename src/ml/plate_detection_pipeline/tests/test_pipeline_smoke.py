import os
import cv2
import pytest
from plate_detect.config import Config
from plate_detect.data.fixtures import make_raw_fixture
from plate_detect.data.prepare import prepare

pytestmark = pytest.mark.slow


def test_full_pipeline_cpu(tmp_path):
    # 1. fixtures → prepare (exercises class-map gate, split, dedup both directions, validate)
    raw = tmp_path / "raw"; make_raw_fixture(str(raw), n_per_split=8, seed=0)
    cfg = Config(
        raw_dir=str(raw), processed_dir=str(tmp_path / "proc"),
        dataset_yaml=str(tmp_path / "a1_det.yaml"), split_dir=str(tmp_path / "split"),
        imgsz=64, epochs=1, batch=2,
    )
    summary = prepare(cfg)
    assert summary["counts"]["train"] == 8
    assert "dup_train_test" in summary and "dup_train_val" in summary
    assert os.path.exists(summary["phash_report"])

    # 2. train 1 epoch on CPU (downloads yolov8n.pt on first run)
    from plate_detect.train.trainer import run_train
    run_dir = run_train("yolov8n", cfg, cfg.dataset_yaml, seed=0,
                        project=str(tmp_path / "runs"), imgsz=64)
    best = os.path.join(run_dir, "weights", "best.pt")
    assert os.path.exists(best)

    # 3. inference via PlateDetector (pt backend) — must not crash
    from plate_detect.inference.plate_detector import PlateDetector
    val_imgs = sorted((tmp_path / "proc" / "images" / "val").glob("*.jpg"))
    assert val_imgs, "prepare() produced no val images — check split logic"
    img = cv2.imread(val_imgs[0].as_posix())
    assert img is not None
    assert isinstance(PlateDetector(best, backend="pt", conf=0.01).detect(img), list)

    # 4. export ONNX + exercise the onnx backend seam (family dispatch + rescale)
    from plate_detect.export.to_onnx import export
    onnx_path = export(best, str(tmp_path / "model.onnx"), imgsz=64)
    assert os.path.exists(onnx_path)
    onnx_dets = PlateDetector(onnx_path, backend="onnx", conf=0.01).detect(img)
    assert isinstance(onnx_dets, list)

    # 5. run_eval on the test split returns the expected metric keys
    from plate_detect.eval.evaluate import run_eval
    m = run_eval(best, cfg.dataset_yaml, imgsz=64, conf=0.01, iou=0.5)
    assert {"map50", "map5095", "precision", "recall"} <= set(m)
