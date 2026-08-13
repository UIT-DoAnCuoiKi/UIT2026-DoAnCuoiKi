import os
from plate_detect.data.fixtures import make_raw_fixture

def test_makes_paired_polygon_dataset(tmp_path):
    make_raw_fixture(str(tmp_path), n_per_split=6, seed=0)
    for split in ("train", "val"):
        imgs = os.listdir(os.path.join(tmp_path, "images", split))
        lbls = os.listdir(os.path.join(tmp_path, "labels", split))
        assert len(imgs) == 6 and len(lbls) == 6
    # a label line has class + 8 polygon coords
    lp = os.path.join(tmp_path, "labels", "train", os.listdir(os.path.join(tmp_path, "labels", "train"))[0])
    parts = open(lp).read().split()
    assert len(parts) == 9
