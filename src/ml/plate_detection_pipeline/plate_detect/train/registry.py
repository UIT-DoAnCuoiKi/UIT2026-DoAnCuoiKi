from __future__ import annotations

MODEL_REGISTRY: dict[str, str] = {
    "yolov8n": "yolov8n.pt",
    "yolo26n": "yolo26n.pt",
}


def resolve(key: str) -> str:
    if key not in MODEL_REGISTRY:
        raise KeyError(f"unknown model '{key}'; valid: {sorted(MODEL_REGISTRY)}")
    return MODEL_REGISTRY[key]
