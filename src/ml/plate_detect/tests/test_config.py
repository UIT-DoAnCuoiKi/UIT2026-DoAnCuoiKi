from plate_detect.config import Config

def test_defaults():
    c = Config()
    assert c.imgsz == 640
    assert c.epochs == 100
    assert c.batch == 16
    assert c.patience == 20
    assert c.seeds == [0, 1, 2]
    assert c.class_names == {0: "bien_1hang", 1: "bien_2hang"}
    assert c.num_classes == 2

def test_load_yaml_override(tmp_path):
    y = tmp_path / "cfg.yaml"
    y.write_text("epochs: 3\nbatch: 2\n")
    c = Config.load(str(y))
    assert c.epochs == 3            # from yaml
    assert c.batch == 2             # from yaml
    assert c.imgsz == 640           # default retained

def test_load_kwargs_override_yaml(tmp_path):
    y = tmp_path / "cfg.yaml"
    y.write_text("epochs: 3\n")
    c = Config.load(str(y), epochs=7)
    assert c.epochs == 7            # kwarg beats yaml
