"""Huấn luyện, đánh giá và xuất model phân loại kiểu dáng xe (Sedan/GamCao/XeTai).

Chạy 2 lượt huấn luyện (ResNet18 và MobileNetV3-Small) trên cùng dữ liệu và
cùng cấu hình để so sánh, dùng GPU nếu có.

Phần phân loại loại thô (car/motorcycle/bus/truck) không huấn luyện ở đây mà
dùng YOLO pretrained, xem src/ml/predict_vehicle.py.

Mỗi lượt lưu ra: checkpoint (.pt), bản ONNX, file history JSON (lịch sử từng
epoch + kết quả test) và 1 dòng trong src/ml/experiments.csv.

Chạy: (môi trường ml-gpu) python src/ml/train_vehicle_classifier.py
"""

from __future__ import annotations

import csv
import datetime
import json
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src" / "ml" / "training"))

import torch  # noqa: E402
from torch.utils.data import DataLoader  # noqa: E402

from classifier import (  # noqa: E402
    benchmark_cpu,
    count_params,
    evaluate,
    export_onnx,
    train_classifier,
)

DATA_DIR = REPO_ROOT / "data" / "processed" / "vehicle-style"
CHECKPOINT_DIR = REPO_ROOT / "src" / "ml" / "checkpoints" / "vehicle-style"
WEIGHTS_DIR = REPO_ROOT / "src" / "ml" / "weights"
EXPERIMENTS_CSV = REPO_ROOT / "src" / "ml" / "experiments.csv"
EXPERIMENTS_DIR = REPO_ROOT / "src" / "ml" / "experiments"

MODELS = ["resnet18", "mobilenet_v3_small"]
EPOCHS = 15
BATCH = 32
LR = 1e-4
DATASET_SOURCE = "B5 (Vehicle Body Style Dataset), gộp 12 kiểu dáng gốc thành 3 lớp"


def main() -> None:
    device = "cuda" if torch.cuda.is_available() else "cpu"
    device_name = torch.cuda.get_device_name(0) if device == "cuda" else "cpu"
    print(f"device: {device} ({device_name})")

    EXPERIMENTS_DIR.mkdir(parents=True, exist_ok=True)
    WEIGHTS_DIR.mkdir(parents=True, exist_ok=True)

    manifest = {
        "epochs": EPOCHS, "batch_size": BATCH, "lr": LR, "optimizer": "Adam",
        "augmentation": "RandomResizedCrop(224, scale=0.8-1.0), RandomHorizontalFlip, "
                         "RandomRotation(10), ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2)",
        "loss": "CrossEntropyLoss(weight=class_weights), trọng số nghịch tỉ lệ số mẫu mỗi lớp",
        "device": f"{device} ({device_name})",
        "models": MODELS,
        "data_source": DATASET_SOURCE,
        "data_dir": str(DATA_DIR.relative_to(REPO_ROOT)),
        "note": "Loại thô (car/motorcycle/bus/truck) dùng một model YOLO pretrained trên COCO "
                "(cụ thể YOLOv8n), không huấn luyện thêm; xem src/ml/predict_vehicle.py",
    }

    rows = []
    for model_name in MODELS:
        print(f"\n===== style / {model_name} =====")
        model, class_names, best_path, test_ds, history = train_classifier(
            data_dir=DATA_DIR, model_name=model_name, epochs=EPOCHS,
            checkpoint_dir=CHECKPOINT_DIR, batch_size=BATCH, lr=LR,
            device=device, resume=False,
        )

        test_loader = DataLoader(test_ds, batch_size=BATCH, shuffle=False)
        res = evaluate(model, test_loader, device)
        print(f"[style/{model_name}] test: accuracy={res['accuracy']:.4f} f1_macro={res['f1_macro']:.4f}")
        print(f"  classes: {class_names}")
        print(f"  confusion matrix:\n{res['confusion_matrix']}")

        onnx_path = WEIGHTS_DIR / f"vehicle-style-{model_name}.onnx"
        export_onnx(model, onnx_path, device="cpu")
        pt_path = WEIGHTS_DIR / f"vehicle-style-{model_name}.pt"
        shutil.copy(best_path, pt_path)

        cpu_ms = benchmark_cpu(model, num_runs=50)
        params = count_params(model)
        onnx_size_mb = round(onnx_path.stat().st_size / 1e6, 2)

        history["class_names"] = class_names
        history["test"] = {
            "accuracy": res["accuracy"], "f1_macro": res["f1_macro"],
            "confusion_matrix": res["confusion_matrix"].tolist(),
        }
        history["params"] = params
        history["onnx_size_mb"] = onnx_size_mb
        history["cpu_ms"] = cpu_ms
        (EXPERIMENTS_DIR / f"style_{model_name}_history.json").write_text(
            json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        rows.append([
            datetime.date.today().isoformat(), model_name, "style",
            DATASET_SOURCE, f"epochs={EPOCHS};batch={BATCH};lr={LR}",
            "", "", "", "",  # mAP50, mAP50-95, precision, recall: cột của detection, không áp dụng
            str(pt_path.relative_to(REPO_ROOT)),
            round(res["accuracy"], 4), round(res["f1_macro"], 4),
            params, onnx_size_mb, round(cpu_ms, 2),
        ])

    (EXPERIMENTS_DIR / "run_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    with open(EXPERIMENTS_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        for row in rows:
            writer.writerow(row)
    print(f"\nĐã ghi {len(rows)} dòng vào {EXPERIMENTS_CSV}")

    print("\n=== Bảng so sánh ===")
    header = ["model", "params", "onnx_MB", "cpu_ms", "accuracy", "f1_macro"]
    print(" ".join(f"{h:>14s}" for h in header))
    for row in rows:
        model_name = row[1]
        pt_path, acc, f1, params, onnx_mb, cpu_ms = row[9], row[10], row[11], row[12], row[13], row[14]
        vals = [model_name, params, onnx_mb, cpu_ms, acc, f1]
        print(" ".join(f"{str(v):>14s}" for v in vals))


if __name__ == "__main__":
    main()
