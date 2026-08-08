from __future__ import annotations
from dataclasses import dataclass, field
import yaml


@dataclass
class Config:
    raw_dir: str = "data/raw/kaggle_vn_plate_segment"
    processed_dir: str = "data/processed/a1_det"
    dataset_yaml: str = "src/ml/plate_detect/configs/a1_det.yaml"
    split_dir: str = "src/ml/plate_detect/configs/split"
    imgsz: int = 640
    epochs: int = 100
    batch: int = 16
    patience: int = 20
    seeds: list[int] = field(default_factory=lambda: [0, 1, 2])
    class_names: dict[int, str] = field(
        default_factory=lambda: {0: "bien_1hang", 1: "bien_2hang"}
    )
    conf: float = 0.25
    iou: float = 0.5
    split_ratios: dict[str, float] = field(
        default_factory=lambda: {"val": 0.5, "test": 0.5}
    )

    @property
    def num_classes(self) -> int:
        return len(self.class_names)

    @classmethod
    def load(cls, path: str | None = None, **overrides) -> "Config":
        data: dict = {}
        if path:
            with open(path) as f:
                data = yaml.safe_load(f) or {}
        data.update({k: v for k, v in overrides.items() if v is not None})
        return cls(**data)
