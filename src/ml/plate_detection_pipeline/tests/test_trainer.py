from plate_detect.config import Config
from plate_detect.train.trainer import run_name, build_train_args

def test_run_name_includes_seed_and_imgsz():
    assert run_name("yolo26n", 2, 960) == "yolo26n_s2_960"

def test_build_train_args_fixed_for_fair_comparison():
    cfg = Config()
    a = build_train_args(cfg, "a1_det.yaml", seed=1, project="runs", name="r", imgsz=640)
    assert a["seed"] == 1 and a["deterministic"] is True
    assert a["imgsz"] == 640 and a["epochs"] == 100 and a["batch"] == 16
    assert a["data"] == "a1_det.yaml" and a["name"] == "r"

def test_build_train_args_imgsz_override():
    a = build_train_args(Config(), "a1.yaml", seed=0, project="p", name="n", imgsz=960)
    assert a["imgsz"] == 960
