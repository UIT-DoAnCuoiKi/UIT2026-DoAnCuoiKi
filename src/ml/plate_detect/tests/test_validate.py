import os
import cv2
import numpy as np
import pytest
from plate_detect.data.validate import validate_processed, assert_valid

def _mk(root, split="train"):
    for sub in ("images", "labels"):
        os.makedirs(os.path.join(root, sub, split), exist_ok=True)

def _write_img(root, split, name):
    cv2.imwrite(os.path.join(root, "images", split, name + ".jpg"),
                np.zeros((32, 32, 3), np.uint8))

def _write_lbl(root, split, name, text):
    with open(os.path.join(root, "labels", split, name + ".txt"), "w") as f:
        f.write(text)

def test_valid_dir(tmp_path):
    r = str(tmp_path); _mk(r)
    _write_img(r, "train", "a"); _write_lbl(r, "train", "a", "0 0.5 0.5 0.2 0.2\n")
    assert validate_processed(r) == []

def test_missing_label(tmp_path):
    r = str(tmp_path); _mk(r)
    _write_img(r, "train", "a")     # no label
    errs = validate_processed(r)
    assert any("label" in e for e in errs)

def test_bad_class_and_range(tmp_path):
    r = str(tmp_path); _mk(r)
    _write_img(r, "train", "a"); _write_lbl(r, "train", "a", "5 0.5 0.5 0.2 0.2\n")
    _write_img(r, "train", "b"); _write_lbl(r, "train", "b", "0 1.7 0.5 0.2 0.2\n")
    errs = validate_processed(r)
    assert any("class" in e for e in errs)
    assert any("range" in e for e in errs)
    with pytest.raises(ValueError):
        assert_valid(r)
