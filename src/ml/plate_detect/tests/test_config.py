from plate_detect.config import Config

def test_defaults():
    c = Config()
    assert c.imgsz == 640 and c.epochs == 100 and c.batch == 16 and c.patience == 20
    assert c.seeds == [0, 1, 2]
    assert c.class_names == {0: "bien_1hang", 1: "bien_2hang"}
    assert c.num_classes == 2
    assert c.split_ratios == {"val": 0.5, "test": 0.5}

def test_load_yaml_then_kwargs_override(tmp_path):
    y = tmp_path / "cfg.yaml"
    y.write_text("epochs: 3\nbatch: 2\n")
    c = Config.load(str(y), batch=8)
    assert c.epochs == 3      # from yaml
    assert c.batch == 8       # kwarg wins over yaml
    assert c.imgsz == 640     # default retained
