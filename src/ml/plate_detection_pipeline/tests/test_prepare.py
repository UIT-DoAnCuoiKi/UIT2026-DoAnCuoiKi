import os
from plate_detect.config import Config
from plate_detect.data.fixtures import make_raw_fixture
from plate_detect.data.prepare import prepare

def _cfg(tmp_path):
    raw = tmp_path / "raw"; make_raw_fixture(str(raw), n_per_split=10, seed=0)
    return Config(
        raw_dir=str(raw), processed_dir=str(tmp_path / "proc"),
        dataset_yaml=str(tmp_path / "a1_det.yaml"), split_dir=str(tmp_path / "split"),
    )

def test_prepare_produces_three_splits_and_yaml(tmp_path):
    cfg = _cfg(tmp_path)
    out = prepare(cfg)
    # raw train kept (10); raw val (10) → val+test ~5/5
    assert out["counts"]["train"] == 10
    assert out["counts"]["val"] + out["counts"]["test"] == 10
    assert os.path.exists(cfg.dataset_yaml)
    for split in ("train", "val", "test"):
        assert os.path.exists(os.path.join(cfg.split_dir, f"{split}.txt"))
    # labels are YOLO bbox now (5 fields), not polygons (9)
    lbl = os.path.join(cfg.processed_dir, "labels", "train")
    first = os.path.join(lbl, sorted(os.listdir(lbl))[0])
    assert len(open(first).read().split()) == 5

def test_prepare_reports_both_dedup_directions_and_writes_report(tmp_path):
    cfg = _cfg(tmp_path)
    out = prepare(cfg)
    assert "dup_train_test" in out and "dup_train_val" in out
    assert os.path.exists(out["phash_report"])
    body = open(out["phash_report"]).read()
    assert "train_vs_test" in body and "train_vs_val" in body

def test_prepare_stratifies_by_majority_class(tmp_path, monkeypatch):
    # capture the labels passed to stratified_split → must be per-image majority class
    import plate_detect.data.prepare as P
    seen = {}
    real = P.stratified_split
    def spy(items, labels, ratios, seed=42):
        seen["labels"] = list(labels)
        return real(items, labels, ratios, seed)
    monkeypatch.setattr(P, "stratified_split", spy)
    prepare(_cfg(tmp_path))
    # fixture alternates class per image → labels are 0/1 (not all 0)
    assert set(seen["labels"]) == {0, 1}
