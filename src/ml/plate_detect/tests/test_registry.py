import pytest
from plate_detect.train.registry import MODEL_REGISTRY, resolve


def test_known_models():
    assert resolve("yolov8n") == "yolov8n.pt"
    assert resolve("yolo26n") == "yolo26n.pt"


def test_unknown_raises():
    with pytest.raises(KeyError):
        resolve("nope")


def test_both_models_present():
    assert {"yolov8n", "yolo26n"} <= set(MODEL_REGISTRY)
