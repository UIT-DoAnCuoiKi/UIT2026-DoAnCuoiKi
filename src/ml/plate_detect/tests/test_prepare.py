# src/ml/plate_detect/tests/test_prepare.py
import os
import yaml
from plate_detect.config import Config
from plate_detect.data.prepare import prepare
from plate_detect.data.validate import validate_processed

def test_prepare_end_to_end(tmp_path, raw_fixture):
    cfg = Config(
        raw_dir=str(raw_fixture),
        processed_dir=str(tmp_path / "proc"),
        dataset_yaml=str(tmp_path / "a1_det.yaml"),
        split_dir=str(tmp_path / "split"),
    )
    summary = prepare(cfg)
    # processed layout exists with train/val/test
    for split in ("train", "val", "test"):
        assert os.path.isdir(os.path.join(cfg.processed_dir, "images", split))
    # dataset yaml written with 2 classes
    y = yaml.safe_load(open(cfg.dataset_yaml))
    assert len(y["names"]) == 2
    # manifests written
    assert os.path.exists(os.path.join(cfg.split_dir, "train.txt"))
    # data contract holds
    assert validate_processed(cfg.processed_dir, cfg.num_classes) == []
    # train kept intact (10 fixture train images), val(10) split into val+test
    assert summary["counts"]["train"] == 10
    assert summary["counts"]["val"] + summary["counts"]["test"] == 10
