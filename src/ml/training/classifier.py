"""Logic huấn luyện, đánh giá và xuất model dùng chung cho bộ phân loại xe.

Dùng bởi src/ml/train_vehicle_classifier.py để huấn luyện và so sánh ResNet18
với MobileNetV3-Small trên bài toán phân loại kiểu dáng xe con, dữ liệu do
src/ml/data_prep/prepare_classification_data.py tạo ra.

Cấu trúc thư mục dữ liệu mong đợi (chuẩn torchvision ImageFolder):
  data_dir/{train,valid,test}/{tên_lớp}/*.jpg

Lưu ý quan trọng: ImageFolder gán chỉ số nhãn theo thứ tự bảng chữ cái của
tên thư mục lớp. Ánh xạ chỉ số <-> tên lớp thật của một lần huấn luyện luôn
là danh sách `class_names` mà train_classifier() trả về và lưu trong
checkpoint. Khi viết code suy luận, đọc từ checkpoint thay vì hard-code.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path

import torch
import torch.nn as nn
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score
from torch.utils.data import DataLoader
from torchvision import datasets, models, transforms

IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]


def build_transforms(train: bool) -> transforms.Compose:
    """Tiền xử lý ảnh. Bản `train=False` phải được dùng lại y nguyên khi suy
    luận, lệch bước nào cũng làm độ chính xác giảm mà không báo lỗi."""
    if train:
        return transforms.Compose([
            transforms.RandomResizedCrop(224, scale=(0.8, 1.0)),
            transforms.RandomHorizontalFlip(),
            transforms.RandomRotation(10),
            transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2),
            transforms.ToTensor(),
            transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
        ])
    return transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
        transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
    ])


def build_model(model_name: str, num_classes: int) -> nn.Module:
    """Tạo model từ trọng số ImageNet, thay lớp phân loại cuối theo num_classes."""
    if model_name == "resnet18":
        model = models.resnet18(weights=models.ResNet18_Weights.IMAGENET1K_V1)
        model.fc = nn.Linear(model.fc.in_features, num_classes)
    elif model_name == "mobilenet_v3_small":
        model = models.mobilenet_v3_small(weights=models.MobileNet_V3_Small_Weights.IMAGENET1K_V1)
        model.classifier[3] = nn.Linear(model.classifier[3].in_features, num_classes)
    else:
        raise ValueError(f"Unknown model_name: {model_name!r}")
    return model


def count_params(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters())


def load_datasets(data_dir: Path):
    """Load 3 split. Kiểm tra 3 split có cùng tập lớp, vì nếu lệch thì chỉ số
    nhãn giữa các split sẽ trỏ sai lớp và mọi metric sau đó đều vô nghĩa."""
    train_ds = datasets.ImageFolder(data_dir / "train", transform=build_transforms(train=True))
    valid_ds = datasets.ImageFolder(data_dir / "valid", transform=build_transforms(train=False))
    test_ds = datasets.ImageFolder(data_dir / "test", transform=build_transforms(train=False))
    assert train_ds.classes == valid_ds.classes == test_ds.classes, (
        "train/valid/test có tập lớp khác nhau, kiểm tra lại data_prep "
        "(có thể do 1 lớp thiếu ảnh ở 1 split nào đó)"
    )
    return train_ds, valid_ds, test_ds


def compute_class_weights(train_ds: datasets.ImageFolder, num_classes: int) -> torch.Tensor:
    """Trọng số lớp tỉ lệ nghịch với số mẫu, để lớp ít ảnh không bị lấn át.

    Công thức: tổng_mẫu / (số_lớp * số_mẫu_lớp_đó), tức lớp có đúng mức trung
    bình sẽ nhận trọng số 1, lớp ít mẫu hơn nhận trọng số lớn hơn 1.
    """
    counts = torch.zeros(num_classes)
    for _, label in train_ds.samples:
        counts[label] += 1
    counts = counts.clamp(min=1)  # chặn chia 0 nếu 1 lớp vắng mặt hoàn toàn ở train
    return counts.sum() / (num_classes * counts)


def train_classifier(
    data_dir: Path,
    model_name: str,
    epochs: int,
    checkpoint_dir: Path,
    batch_size: int = 32,
    lr: float = 1e-4,
    device: str | None = None,
    resume: bool = False,
):
    """Trả về (model, class_names, best_path, test_ds, history).

    `history` là dict phục vụ notebook thu hoạch:
      {"epochs": [{"epoch", "train_loss", "val_acc", "val_f1_macro"}, ...],
       "started_at": iso8601, "finished_at": iso8601, "train_seconds": float}
    """
    device = device or ("cuda" if torch.cuda.is_available() else "cpu")
    data_dir = Path(data_dir)
    checkpoint_dir = Path(checkpoint_dir)
    checkpoint_dir.mkdir(parents=True, exist_ok=True)

    train_ds, valid_ds, test_ds = load_datasets(data_dir)
    class_names = train_ds.classes
    num_classes = len(class_names)
    print(f"[{model_name}] {num_classes} lop: {class_names}")

    class_weights = compute_class_weights(train_ds, num_classes).to(device)

    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True, num_workers=2)
    valid_loader = DataLoader(valid_ds, batch_size=batch_size, shuffle=False, num_workers=2)

    model = build_model(model_name, num_classes).to(device)
    criterion = nn.CrossEntropyLoss(weight=class_weights)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)

    ckpt_path = checkpoint_dir / f"{model_name}_last.pt"
    start_epoch = 0
    epoch_history: list[dict] = []
    if resume and ckpt_path.exists():
        ckpt = torch.load(ckpt_path, map_location=device)
        model.load_state_dict(ckpt["model_state"])
        optimizer.load_state_dict(ckpt["optimizer_state"])
        start_epoch = ckpt["epoch"] + 1
        epoch_history = ckpt.get("epoch_history", [])
        print(f"Resume tu epoch {start_epoch}")

    started_at = datetime.now(timezone.utc)
    t0 = time.perf_counter()

    for epoch in range(start_epoch, epochs):
        model.train()
        running_loss = 0.0
        for imgs, labels in train_loader:
            imgs, labels = imgs.to(device), labels.to(device)
            optimizer.zero_grad()
            outputs = model(imgs)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
            running_loss += loss.item() * imgs.size(0)

        train_loss = running_loss / len(train_ds)
        val_metrics = evaluate(model, valid_loader, device)
        print(
            f"[{model_name}] epoch {epoch + 1}/{epochs} "
            f"train_loss={train_loss:.4f} val_acc={val_metrics['accuracy']:.4f} "
            f"val_f1_macro={val_metrics['f1_macro']:.4f}"
        )
        epoch_history.append({
            "epoch": epoch + 1,
            "train_loss": train_loss,
            "val_acc": val_metrics["accuracy"],
            "val_f1_macro": val_metrics["f1_macro"],
        })

        torch.save(
            {
                "epoch": epoch,
                "model_state": model.state_dict(),
                "optimizer_state": optimizer.state_dict(),
                "class_names": class_names,
                "epoch_history": epoch_history,
            },
            ckpt_path,
        )

    train_seconds = time.perf_counter() - t0
    finished_at = datetime.now(timezone.utc)
    history = {
        "epochs": epoch_history,
        "started_at": started_at.isoformat(),
        "finished_at": finished_at.isoformat(),
        "train_seconds": train_seconds,
    }

    best_path = checkpoint_dir / f"{model_name}_best.pt"
    torch.save({"model_state": model.state_dict(), "class_names": class_names}, best_path)
    return model, class_names, best_path, test_ds, history


def evaluate(model: nn.Module, loader: DataLoader, device: str) -> dict:
    """Đánh giá trên 1 loader, trả về accuracy, F1-macro, ma trận nhầm lẫn và
    cả y_true/y_pred thô để nơi gọi tự tính thêm chỉ số khác nếu cần."""
    model.eval()
    all_preds: list[int] = []
    all_labels: list[int] = []
    with torch.no_grad():
        for imgs, labels in loader:
            imgs = imgs.to(device)
            preds = model(imgs).argmax(dim=1).cpu().tolist()
            all_preds.extend(preds)
            all_labels.extend(labels.tolist())

    # Truyền labels tường minh cho confusion_matrix để ma trận luôn đủ kích
    # thước, kể cả khi có lớp không xuất hiện trong tập đánh giá
    n_classes = max(all_labels + all_preds, default=-1) + 1
    return {
        "accuracy": accuracy_score(all_labels, all_preds),
        "f1_macro": f1_score(all_labels, all_preds, average="macro"),
        "confusion_matrix": confusion_matrix(all_labels, all_preds, labels=list(range(n_classes))),
        "y_true": all_labels,
        "y_pred": all_preds,
    }


def export_onnx(model: nn.Module, out_path: Path, device: str = "cpu") -> Path:
    """Xuất ONNX để triển khai bằng ONNX Runtime. Cần cài sẵn gói `onnx`."""
    model = model.to(device).eval()
    dummy = torch.randn(1, 3, 224, 224, device=device)
    torch.onnx.export(
        model, dummy, str(out_path),
        input_names=["input"], output_names=["logits"], opset_version=17,
        dynamo=False,  # torch>=2.9 mặc định dùng dynamo exporter, cần thêm onnxscript
    )
    return out_path


def benchmark_cpu(model: nn.Module, num_runs: int = 50) -> float:
    """Thời gian suy luận CPU trung bình (ms/ảnh), đo trên máy huấn luyện.

    Đây không phải số đo trên Raspberry Pi 5, chỉ dùng để so sánh tương đối
    giữa các kiến trúc trên cùng một máy.
    """
    model = model.to("cpu").eval()
    dummy = torch.randn(1, 3, 224, 224)
    with torch.no_grad():
        for _ in range(5):  # chạy không tính giờ để làm nóng, tránh lệch số đo
            model(dummy)
        start = time.perf_counter()
        for _ in range(num_runs):
            model(dummy)
        elapsed = time.perf_counter() - start
    return (elapsed / num_runs) * 1000
