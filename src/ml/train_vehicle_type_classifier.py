"""Huấn luyện, đánh giá và xuất model phân loại LOẠI XE THÔ (car/motorbike/truck).

Thay cho việc dùng thẳng nhãn lớp của YOLOv8n pretrained trên COCO (không train
lại, sai nhiều với ảnh cận cảnh kiểu camera cổng — từng gây lỗi map sai xe
máy). Dữ liệu do src/ml/data_prep/prepare_vehicle_type_dataset.py tạo ra từ
data/raw/kaggle_vn_plate_segment (xem docstring file đó để biết nguồn từng
lớp và cách lọc lớp xe tải bằng tay). Không có lớp "bus" ở bản đầu này — dữ
liệu hiện có không đủ ảnh xe khách cận cảnh giống góc camera cổng, xem lại khi
có thêm nguồn bù.

Chạy 2 lượt huấn luyện (ResNet18 và MobileNetV3-Small) trên cùng dữ liệu và
cùng cấu hình để so sánh — giống hệt quy trình đã dùng cho model kiểu dáng xe
con (train_vehicle_classifier.py), dùng chung classifier.py.

Mỗi lượt lưu ra: checkpoint (.pt), bản ONNX, file history JSON (lịch sử từng
epoch + kết quả test) và 1 dòng trong src/ml/experiments.csv.

Chạy: (môi trường ml-gpu, khuyến nghị Colab GPU) python src/ml/train_vehicle_type_classifier.py
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

DATA_DIR = REPO_ROOT / "data" / "processed" / "vehicle-type"
CHECKPOINT_DIR = REPO_ROOT / "src" / "ml" / "checkpoints" / "vehicle-type"
WEIGHTS_DIR = REPO_ROOT / "src" / "ml" / "weights"
EXPERIMENTS_CSV = REPO_ROOT / "src" / "ml" / "experiments.csv"
EXPERIMENTS_DIR = REPO_ROOT / "src" / "ml" / "experiments"

MODELS = ["resnet18", "mobilenet_v3_small"]
EPOCHS = 15
BATCH = 32
LR = 1e-4
DATASET_SOURCE = (
    "kaggle_vn_plate_segment: carlong_ + 92 anh Dieu_/Hung_ (car), greenpack_ + 128 anh "
    "Dieu_/Hung_ (motorbike), 73 anh Dieu_/Hung_ (truck) - moi lop tron ca 2 phong cach anh "
    "(cong barrier/CCTV VA duong pho) sau khi phat hien ban dau (chi 1 nguon/lop) khien model "
    "hoc tat theo phong cach anh thay vi hinh dang xe (xem prepare_vehicle_type_dataset.py va "
    "sanity_check_vehicle_type_ood.py)"
)


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
        "loss": "CrossEntropyLoss(weight=class_weights), trong so nghich ti le so mau moi lop "
                "(lop truck it anh hon nhieu, class_weights bu lai)",
        "device": f"{device} ({device_name})",
        "models": MODELS,
        "data_source": DATASET_SOURCE,
        "data_dir": str(DATA_DIR.relative_to(REPO_ROOT)),
        "note": "Thay the YOLOv8n pretrained COCO (khong train lai) dang dung trong "
                "predict_vehicle.detect_vehicle_crop de suy loai xe tho; YOLOv8n van dung de "
                "tim/cat vung xe, chi bo phan doc nhan lop COCO cua no.",
    }

    rows = []
    for model_name in MODELS:
        print(f"\n===== type / {model_name} =====")
        model, class_names, best_path, test_ds, history = train_classifier(
            data_dir=DATA_DIR, model_name=model_name, epochs=EPOCHS,
            checkpoint_dir=CHECKPOINT_DIR, batch_size=BATCH, lr=LR,
            device=device, resume=False,
        )

        test_loader = DataLoader(test_ds, batch_size=BATCH, shuffle=False)
        res = evaluate(model, test_loader, device)
        print(f"[type/{model_name}] test: accuracy={res['accuracy']:.4f} f1_macro={res['f1_macro']:.4f}")
        print(f"  classes: {class_names}")
        print(f"  confusion matrix:\n{res['confusion_matrix']}")

        onnx_path = WEIGHTS_DIR / f"vehicle-type-{model_name}.onnx"
        export_onnx(model, onnx_path, device="cpu")
        pt_path = WEIGHTS_DIR / f"vehicle-type-{model_name}.pt"
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
        (EXPERIMENTS_DIR / f"type_{model_name}_history.json").write_text(
            json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        rows.append([
            datetime.date.today().isoformat(), model_name, "type",
            DATASET_SOURCE, f"epochs={EPOCHS};batch={BATCH};lr={LR}",
            "", "", "", "",  # mAP50, mAP50-95, precision, recall: cot cua detection, khong ap dung
            str(pt_path.relative_to(REPO_ROOT)),
            round(res["accuracy"], 4), round(res["f1_macro"], 4),
            params, onnx_size_mb, round(cpu_ms, 2),
        ])

    (EXPERIMENTS_DIR / "type_run_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    with open(EXPERIMENTS_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        for row in rows:
            writer.writerow(row)
    print(f"\nDa ghi {len(rows)} dong vao {EXPERIMENTS_CSV}")

    print("\n=== Bang so sanh ===")
    header = ["model", "params", "onnx_MB", "cpu_ms", "accuracy", "f1_macro"]
    print(" ".join(f"{h:>14s}" for h in header))
    for row in rows:
        model_name = row[1]
        pt_path, acc, f1, params, onnx_mb, cpu_ms = row[9], row[10], row[11], row[12], row[13], row[14]
        vals = [model_name, params, onnx_mb, cpu_ms, acc, f1]
        print(" ".join(f"{str(v):>14s}" for v in vals))


if __name__ == "__main__":
    main()
