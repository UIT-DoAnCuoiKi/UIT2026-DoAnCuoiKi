"""CRNN nhỏ (CNN + BiLSTM + CTC) tự huấn luyện để đọc 1 dòng ký tự biển số,
dùng chung cho train/eval/export của `src/ml/train_ocr_crnn.py`.

Khác với RapidOCR/EasyOCR (model tổng quát, charset rộng, vài chục triệu
tham số), model này chỉ cần nhận diện 36 ký tự (0-9, A-Z) trên 1 dòng văn bản
ngắn (3-9 ký tự) nên có thể rất nhỏ, phù hợp mục tiêu chạy trên thiết bị biên
cấu hình thấp (Raspberry Pi 5).

Quy ước dữ liệu: mỗi mẫu huấn luyện là 1 DÒNG đơn (không phải cả biển số).
Biển 2 dòng được `PlateRowDataset` tách thành 2 mẫu dòng riêng (trên/dưới)
ngay từ bước nạp dữ liệu, dùng đúng `split_rows()` của
`src/ml/pipeline/ocr.py` để khớp với xử lý lúc suy luận.
"""

from __future__ import annotations

import re
import string
import time
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pipeline.ocr import deskew, preprocess_for_ocr, split_rows  # noqa: E402

CHARSET = sorted(string.digits + string.ascii_uppercase)  # 36 ký tự
CHAR_TO_IDX = {c: i + 1 for i, c in enumerate(CHARSET)}  # 0 dành cho blank CTC
IDX_TO_CHAR = {i + 1: c for i, c in enumerate(CHARSET)}
NUM_CLASSES = len(CHARSET) + 1  # +1 blank

IMG_HEIGHT = 48
IMG_WIDTH = 128

# Phân phối thực nghiệm số pixel mỗi dòng ký tự của crop THẬT trong topkek
# (đo trên data/processed/plate-ocr/train.csv). Dùng làm mục tiêu khi hạ cấp
# ảnh sinh tổng hợp: ảnh sinh tổng hợp vốn 100% đạt >=40px/dòng và sạch tinh,
# lệch hẳn so với ảnh thật (trung vị 19px/dòng, chỉ 7% đạt >=40px).
REAL_PX_PER_ROW_PERCENTILES = [10, 13, 19, 26, 36]  # p10, p25, p50, p75, p90


def split_label_for_2row_from_raw(label_raw: str) -> tuple[str, str] | None:
    """Tách nhãn dòng trên/dòng dưới theo đúng dấu cách trong nhãn gốc.

    Nhãn gốc của topkek (cột `label_raw`, trước khi bỏ dấu cách để tạo
    `label_clean`) giữ nguyên dấu cách ở đúng ranh giới 2 dòng, ví dụ
    "60F1 64727" -> dòng trên "60F1", dòng dưới "64727". Xác nhận qua toàn
    bộ 3.816/3.817 biển 2 dòng trong tập train đều có dấu cách này, và trùng
    khớp với ảnh thật khi đối chiếu bằng mắt.

    Đây là nguồn thật, không phải suy đoán. Thay cho cách cũ (đoán theo độ
    dài, thử top_len=3 trước rồi 4) từng làm sai 405/3.817 = 10,6% nhãn biển
    2 dòng: nhãn 8 ký tự có thể là 3+5 hoặc 4+4, chuỗi không đủ thông tin để
    phân biệt hai khả năng này, cách đoán cũ luôn chọn 3+5 nên sai mọi
    trường hợp 4+4.

    Trả về None nếu không tách được (không có dấu cách, hiếm gặp, ~0,03%),
    để nơi gọi tự quyết định phương án dự phòng.
    """
    parts = str(label_raw).split(" ", 1)
    if len(parts) != 2:
        return None
    top = re.sub(r"[^A-Z0-9]", "", parts[0].upper())
    bottom = re.sub(r"[^A-Z0-9]", "", parts[1].upper())
    if not top or not bottom:
        return None
    return top, bottom


def encode_label(label: str) -> list[int]:
    return [CHAR_TO_IDX[c] for c in label if c in CHAR_TO_IDX]


def decode_greedy(logits: torch.Tensor) -> list[str]:
    """Giải mã CTC kiểu greedy: argmax mỗi bước thời gian, gộp ký tự lặp liên
    tiếp, bỏ blank. `logits` dạng (B, T, C)."""
    ids = logits.argmax(dim=2).cpu().numpy()  # (B, T)
    texts = []
    for seq in ids:
        chars = []
        prev = -1
        for idx in seq:
            if idx != prev and idx != 0:
                chars.append(IDX_TO_CHAR.get(int(idx), ""))
            prev = idx
        texts.append("".join(chars))
    return texts


def _load_row_image(image_path: str, layout: str, row: str | None) -> np.ndarray:
    img = cv2.imread(image_path)
    img = deskew(img)
    if row is None:
        return img
    top, bottom = split_rows(img)
    return top if row == "top" else bottom


class PlateRowDataset(Dataset):
    """Mỗi phần tử là 1 dòng ký tự đơn: (ảnh_đã_chuẩn_hoá, nhãn_mã_hoá).

    Biển 1 dòng -> 1 mẫu/dòng CSV. Biển 2 dòng -> 2 mẫu/dòng CSV (trên, dưới),
    nhãn dòng lấy từ dấu cách trong `label_raw` (xem
    `split_label_for_2row_from_raw`). `augment=True` bật biến đổi nhẹ (xoay,
    sáng/tối, nhiễu Gauss) để tăng đa dạng lúc huấn luyện.
    """

    def __init__(self, csv_paths: list[Path], augment: bool = False,
                 min_px_per_row: float = 0.0, degrade_synthetic: bool = False):
        """`min_px_per_row` loại các crop quá nhỏ (thí nghiệm cho thấy lọc như
        vậy làm kết quả xấu đi vì mất dữ liệu gây overfit, để mặc định tắt).

        `degrade_synthetic` bật việc hạ cấp ảnh sinh tổng hợp cho giống phân
        phối ảnh thật, xem `_degrade_synthetic()`.
        """
        self.augment = augment
        self.degrade_synthetic = degrade_synthetic
        self.samples: list[tuple[str, str, str | None, str, str]] = []
        for csv_path in csv_paths:
            df = pd.read_csv(csv_path)
            for _, r in df.iterrows():
                if min_px_per_row:
                    px_per_row = r.height / 2 if r.layout == "bien_2hang" else r.height
                    if px_per_row < min_px_per_row:
                        continue
                source = getattr(r, "source", "unknown")
                if r.layout == "bien_2hang":
                    split = split_label_for_2row_from_raw(getattr(r, "label_raw", ""))
                    if split is None:
                        # Hiếm gặp (~0,03% dữ liệu): nhãn gốc không có dấu
                        # cách. Chia đôi theo tỉ lệ 40/60 làm phương án dự
                        # phòng, không có căn cứ định dạng chắc chắn, chấp
                        # nhận vì ảnh hưởng cỡ vài mẫu trên toàn tập.
                        n = len(r.label_clean)
                        split_at = max(1, round(n * 0.4))
                        split = r.label_clean[:split_at], r.label_clean[split_at:]
                    top_label, bottom_label = split
                    self.samples.append((r.image_path, top_label, "top", r.layout, source))
                    self.samples.append((r.image_path, bottom_label, "bottom", r.layout, source))
                else:
                    self.samples.append((r.image_path, r.label_clean, None, r.layout, source))

    def __len__(self) -> int:
        return len(self.samples)

    def _degrade_synthetic(self, img: np.ndarray, rows_of_text: int) -> np.ndarray:
        """Hạ cấp ảnh sinh tổng hợp cho giống phân phối ảnh thật.

        Ảnh sinh tổng hợp của topkek là biển render sạch, 100% đạt >=40px mỗi
        dòng ký tự, trong khi crop thật có trung vị chỉ 19px/dòng và nhiều
        nhiễu. Nếu để nguyên thì một nửa dữ liệu huấn luyện dạy model một phân
        phối không bao giờ gặp ngoài thực tế.

        Mô phỏng đúng cách ảnh thật mất thông tin, theo thứ tự vật lý:
        thu nhỏ về độ phân giải thật (mất chi tiết, không hồi phục được) rồi
        thêm nhiễu cảm biến và nhiễu nén JPEG. Bước phóng to trở lại do
        `preprocess_for_ocr` đảm nhiệm ở lời gọi sau, giống hệt lúc suy luận.
        """
        h, w = img.shape[:2]
        if h < 4 or w < 4:
            return img

        # Lấy ngẫu nhiên mức px/dòng mục tiêu theo phân phối thật, nội suy
        # tuyến tính giữa các phân vị đã đo
        target_px_per_row = float(np.interp(
            np.random.rand(), [0.10, 0.25, 0.50, 0.75, 0.90], REAL_PX_PER_ROW_PERCENTILES
        ))
        target_h = max(4, int(round(target_px_per_row * rows_of_text)))
        if target_h < h:
            scale = target_h / h
            small = cv2.resize(img, (max(4, int(w * scale)), target_h),
                               interpolation=cv2.INTER_AREA)
        else:
            small = img

        if np.random.rand() < 0.5:
            noise = np.random.normal(0, np.random.uniform(2, 8), small.shape)
            small = np.clip(small.astype(np.float32) + noise, 0, 255).astype(np.uint8)

        quality = int(np.random.uniform(30, 70))
        ok, buf = cv2.imencode(".jpg", small, [cv2.IMWRITE_JPEG_QUALITY, quality])
        if ok:
            small = cv2.imdecode(buf, cv2.IMREAD_COLOR)
        return small

    def _augment(self, img: np.ndarray) -> np.ndarray:
        h, w = img.shape[:2]
        angle = np.random.uniform(-4, 4)
        rot_matrix = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
        img = cv2.warpAffine(img, rot_matrix, (w, h), borderMode=cv2.BORDER_REPLICATE)

        # Biến dạng phối cảnh nhẹ: ảnh ở cổng bãi xe hầu như luôn chụp chéo,
        # nên model cần chịu được phần nghiêng còn sót lại kể cả sau khi nắn
        if np.random.rand() < 0.5:
            jitter = min(h, w) * 0.06
            src = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
            dst = src + np.random.uniform(-jitter, jitter, src.shape).astype(np.float32)
            img = cv2.warpPerspective(img, cv2.getPerspectiveTransform(src, dst), (w, h),
                                      borderMode=cv2.BORDER_REPLICATE)

        beta = np.random.uniform(-25, 25)
        img = cv2.convertScaleAbs(img, alpha=1.0, beta=beta)
        if np.random.rand() < 0.3:
            img = cv2.GaussianBlur(img, (3, 3), 0)
        return img

    def __getitem__(self, idx: int):
        image_path, label, row, layout, source = self.samples[idx]
        img = _load_row_image(image_path, layout, row)
        # Hạ cấp trước khi phóng về chiều cao chuẩn, để việc mất chi tiết là
        # thật chứ không bị bước phóng to che mất
        if self.degrade_synthetic and source == "topkek_synthetic":
            img = self._degrade_synthetic(img, rows_of_text=1)
        img = preprocess_for_ocr(img, target_height=IMG_HEIGHT)
        if self.augment:
            img = self._augment(img)
        img = cv2.resize(img, (IMG_WIDTH, IMG_HEIGHT), interpolation=cv2.INTER_LINEAR)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0
        tensor = torch.from_numpy(gray).unsqueeze(0)  # (1, H, W)
        target = torch.tensor(encode_label(label), dtype=torch.long)
        return tensor, target, label


def collate_fn(batch):
    images = torch.stack([b[0] for b in batch])
    targets = torch.cat([b[1] for b in batch])
    target_lengths = torch.tensor([len(b[1]) for b in batch], dtype=torch.long)
    labels = [b[2] for b in batch]
    return images, targets, target_lengths, labels


class CRNN(nn.Module):
    """CNN nhẹ (5 lớp conv) + 1 lớp BiLSTM + CTC head. Với IMG_HEIGHT=48,
    chuỗi đặc trưng đầu ra có độ dài cố định 32 bước thời gian (đủ dư so với
    nhãn dài nhất ~9 ký tự để CTC có chỗ chèn blank)."""

    def __init__(self, num_classes: int = NUM_CLASSES, hidden: int = 96):
        super().__init__()
        self.cnn = nn.Sequential(
            nn.Conv2d(1, 32, 3, 1, 1), nn.BatchNorm2d(32), nn.ReLU(inplace=True), nn.MaxPool2d(2, 2),
            nn.Conv2d(32, 64, 3, 1, 1), nn.BatchNorm2d(64), nn.ReLU(inplace=True), nn.MaxPool2d(2, 2),
            nn.Conv2d(64, hidden, 3, 1, 1), nn.BatchNorm2d(hidden), nn.ReLU(inplace=True),
            nn.MaxPool2d((2, 1), (2, 1)),
            nn.Conv2d(hidden, hidden, 3, 1, 1), nn.BatchNorm2d(hidden), nn.ReLU(inplace=True),
            nn.MaxPool2d((2, 1), (2, 1)),
            nn.Conv2d(hidden, hidden, 3, 1, 1), nn.BatchNorm2d(hidden), nn.ReLU(inplace=True),
        )
        self.height_reduce = nn.Conv2d(hidden, hidden, kernel_size=(3, 1))
        self.rnn = nn.LSTM(hidden, hidden, num_layers=1, bidirectional=True, batch_first=True)
        self.fc = nn.Linear(hidden * 2, num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        feat = self.cnn(x)                    # (B, C, 3, W')
        feat = self.height_reduce(feat)        # (B, C, 1, W')
        feat = feat.squeeze(2).permute(0, 2, 1)  # (B, W', C)
        seq, _ = self.rnn(feat)
        return self.fc(seq)                    # (B, W', num_classes) - logits thô


def count_params(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters())


def train_crnn(
    train_csvs: list[Path],
    val_csvs: list[Path],
    epochs: int,
    checkpoint_dir: Path,
    batch_size: int = 64,
    lr: float = 1e-3,
    device: str | None = None,
    train_synthetic_csv: Path | None = None,
    min_px_per_row: float = 0.0,
    checkpoint_name: str = "crnn_best.pt",
    degrade_synthetic: bool = False,
    seed: int = 42,
):
    """Trả về (model, best_path, history). `history` gồm epoch_history (list
    {epoch, train_loss, val_row_cer, val_row_exact}) và thời gian huấn luyện,
    phục vụ notebook thu hoạch giống các module classifier khác.

    `seed` cố định khởi tạo trọng số, thứ tự xáo trộn dữ liệu và các phép
    augmentation ngẫu nhiên, để 2 lần chạy cùng cấu hình cho kết quả lặp lại
    được, và để so sánh giữa các cấu hình khác nhau không lẫn với nhiễu ngẫu
    nhiên giữa các lần train.
    """
    torch.manual_seed(seed)
    np.random.seed(seed)
    device = device or ("cuda" if torch.cuda.is_available() else "cpu")
    checkpoint_dir = Path(checkpoint_dir)
    checkpoint_dir.mkdir(parents=True, exist_ok=True)

    csvs = list(train_csvs) + ([train_synthetic_csv] if train_synthetic_csv else [])
    train_ds = PlateRowDataset(csvs, augment=True, min_px_per_row=min_px_per_row,
                               degrade_synthetic=degrade_synthetic)
    # Val giữ nguyên toàn bộ, không lọc, không hạ cấp, để so sánh giữa các lần
    # train là công bằng
    val_ds = PlateRowDataset(val_csvs, augment=False)
    print(f"train: {len(train_ds)} dòng, val: {len(val_ds)} dòng")

    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True,
                              num_workers=2, collate_fn=collate_fn)
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False,
                            num_workers=2, collate_fn=collate_fn)

    model = CRNN().to(device)
    criterion = nn.CTCLoss(blank=0, zero_infinity=True)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)

    best_cer = float("inf")
    best_path = checkpoint_dir / checkpoint_name
    epoch_history = []
    started_at = datetime.now(timezone.utc)
    t0 = time.perf_counter()

    for epoch in range(epochs):
        model.train()
        running_loss = 0.0
        for images, targets, target_lengths, _ in train_loader:
            images, targets = images.to(device), targets.to(device)
            optimizer.zero_grad()
            logits = model(images)  # (B, T, C)
            log_probs = torch.log_softmax(logits, dim=2).permute(1, 0, 2)  # (T, B, C) - CTCLoss cần dạng này
            input_lengths = torch.full((images.size(0),), log_probs.size(0), dtype=torch.long)
            loss = criterion(log_probs, targets, input_lengths, target_lengths)
            loss.backward()
            optimizer.step()
            running_loss += loss.item() * images.size(0)
        train_loss = running_loss / len(train_ds)

        val_cer, val_exact = evaluate_rows(model, val_loader, device)
        print(f"epoch {epoch + 1}/{epochs} train_loss={train_loss:.4f} "
              f"val_row_cer={val_cer:.4f} val_row_exact={val_exact:.4f}")
        epoch_history.append({
            "epoch": epoch + 1, "train_loss": train_loss,
            "val_row_cer": val_cer, "val_row_exact": val_exact,
        })
        if val_cer < best_cer:
            best_cer = val_cer
            torch.save({"model_state": model.state_dict(), "charset": CHARSET}, best_path)

    train_seconds = time.perf_counter() - t0
    history = {
        "epochs": epoch_history,
        "started_at": started_at.isoformat(),
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "train_seconds": train_seconds,
    }
    return model, best_path, history


def evaluate_rows(model: nn.Module, loader: DataLoader, device: str) -> tuple[float, float]:
    """CER và accuracy khớp tuyệt đối ở MỨC DÒNG (không phải mức cả biển) -
    dùng để theo dõi trong lúc huấn luyện; đánh giá mức biển thật nằm ở
    `src/ml/eval_ocr_crnn.py` (ghép dòng trên+dưới qua `read_plate`)."""
    from pipeline.ocr import char_error_rate

    model.eval()
    cer_sum, exact, n = 0.0, 0, 0
    with torch.no_grad():
        for images, _, _, labels in loader:
            images = images.to(device)
            logits = model(images)
            preds = decode_greedy(logits)
            for pred, gold in zip(preds, labels):
                cer_sum += char_error_rate(pred, gold)
                exact += int(pred == gold)
                n += 1
    return cer_sum / n, exact / n


def export_onnx(model: nn.Module, out_path: Path, device: str = "cpu") -> Path:
    model = model.to(device).eval()
    dummy = torch.randn(1, 1, IMG_HEIGHT, IMG_WIDTH, device=device)
    torch.onnx.export(
        model, dummy, str(out_path),
        input_names=["input"], output_names=["logits"], opset_version=17,
        dynamo=False,  # torch>=2.9 mặc định dùng dynamo exporter, cần thêm onnxscript
    )
    return out_path


def benchmark_cpu(model: nn.Module, num_runs: int = 50) -> float:
    model = model.to("cpu").eval()
    dummy = torch.randn(1, 1, IMG_HEIGHT, IMG_WIDTH)
    with torch.no_grad():
        for _ in range(5):
            model(dummy)
        start = time.perf_counter()
        for _ in range(num_runs):
            model(dummy)
        elapsed = time.perf_counter() - start
    return (elapsed / num_runs) * 1000
