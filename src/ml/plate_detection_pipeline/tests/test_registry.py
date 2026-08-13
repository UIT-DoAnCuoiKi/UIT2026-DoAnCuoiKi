import pytest
from plate_detect.train.registry import MODEL_REGISTRY, resolve

def test_known_models():
    assert set(MODEL_REGISTRY) == {"yolov8n", "yolo26n"}
    assert resolve("yolo26n") == "yolo26n.pt"

def test_unknown_raises():
    with pytest.raises(KeyError):
        resolve("nope")
