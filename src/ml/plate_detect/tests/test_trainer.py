from plate_detect.config import Config
from plate_detect.train.trainer import build_train_args


def test_build_train_args_fair_and_fixed():
    cfg = Config(imgsz=640, epochs=100, batch=16, patience=20)
    args = build_train_args(cfg, "d.yaml", seed=1, project="runs", name="yolo26n_s1")
    assert args["data"] == "d.yaml"
    assert args["imgsz"] == 640
    assert args["epochs"] == 100
    assert args["batch"] == 16          # fixed, not -1/auto
    assert args["patience"] == 20
    assert args["seed"] == 1
    assert args["deterministic"] is True
    assert args["close_mosaic"] == 10
    assert args["name"] == "yolo26n_s1"


def test_build_train_args_seed_varies():
    cfg = Config()
    a0 = build_train_args(cfg, "d.yaml", 0, "runs", "m_s0")
    a2 = build_train_args(cfg, "d.yaml", 2, "runs", "m_s2")
    assert a0["seed"] == 0 and a2["seed"] == 2


def test_run_name_encodes_model_and_seed():
    from plate_detect.train.trainer import run_name
    assert run_name("yolo26n", 1) == "yolo26n_s1"
    assert run_name("yolov8n", 0) == "yolov8n_s0"
