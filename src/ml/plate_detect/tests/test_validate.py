import os
from plate_detect.data.validate import validate_processed, assert_valid
import pytest

def _write(root, split, stem, img=True, label="0 0.5 0.5 0.2 0.2"):
    os.makedirs(os.path.join(root, "images", split), exist_ok=True)
    os.makedirs(os.path.join(root, "labels", split), exist_ok=True)
    if img:
        open(os.path.join(root, "images", split, stem + ".jpg"), "wb").close()
    if label is not None:
        with open(os.path.join(root, "labels", split, stem + ".txt"), "w") as f:
            f.write(label + "\n")

def test_clean_dataset_has_no_errors(tmp_path):
    _write(str(tmp_path), "train", "a")
    assert validate_processed(str(tmp_path)) == []

def test_flags_orphan_and_out_of_range(tmp_path):
    _write(str(tmp_path), "train", "a", img=False)          # orphan label
    _write(str(tmp_path), "val", "b", label="9 0.5 0.5 0.1 0.1")  # bad class
    _write(str(tmp_path), "test", "c", label="0 1.4 0.5 0.1 0.1") # coord > 1
    errs = validate_processed(str(tmp_path))
    assert any("orphan" in e for e in errs)
    assert any("out of range" in e for e in errs)
    with pytest.raises(ValueError):
        assert_valid(str(tmp_path))
