"""Đọc ký tự biển số (OCR) cho cả biển 1 dòng (ô tô, "ngang") và 2 dòng (xe
máy, "dọc"), theo đúng thứ tự bước đã chốt cho pipeline nhận diện: nhận crop
biển số từ `PlateDetector` (module `plate_detection_pipeline`) → chỉnh nghiêng
→ tách dòng nếu là biển 2 dòng → OCR từng dòng → ghép chuỗi → chuẩn hoá theo
quy tắc ký tự biển số Việt Nam.

Module này chỉ định nghĩa các bước xử lý ảnh + bộ nhận dạng (recognizer) dùng
chung, không ràng buộc cứng vào một engine OCR cụ thể: `RapidOCRRecognizer`,
`EasyOCRRecognizer` và `CRNNRecognizer` đều cài cùng interface
`recognize(image_bgr) -> (text, confidence)` nên có thể hoán đổi hoặc so sánh
với nhau qua cùng một hàm `read_plate()`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import cv2
import numpy as np

# 20 chữ cái hợp lệ trong seri biển số VN (không dùng I, J, O, Q, R, W)
VALID_SERIES_LETTERS = "ABCDEFGHKLMNPSTUVXYZ"

# Nhầm lẫn OCR phổ biến, sửa theo vị trí kỳ vọng: vị trí số luôn quy về chữ số,
# vị trí chữ cái seri (index 2) luôn quy về chữ cái.
DIGIT_POSITION_CONFUSION = {"O": "0", "I": "1", "B": "8", "S": "5", "Z": "2"}
LETTER_POSITION_CONFUSION = {"0": "D", "1": "L"}  # O không xuất hiện trong seri nên không map 0->O

# Seri biển số có thể gồm 1 chữ cái (biển thường, vd 51F) hoặc 2 chữ cái (biển
# seri đặc biệt, vd 50LD-044.11, 80NG-123.45). Cố ý KHÔNG chốt danh sách cứng
# các seri 2 chữ cái: ngoài LD, DA, NG, QT, NN còn nhiều ký hiệu khác đang lưu
# hành, và với một bộ kiểm tra định dạng thì loại nhầm biển hợp lệ gây hại hơn
# là chấp nhận một seri lạ.
KNOWN_SPECIAL_SERIES = ("LD", "DA", "NG", "QT", "NN")  # chỉ để tham khảo, không lọc

# Chuỗi ghép: mã tỉnh (2 số) + seri (1-2 chữ) + số thứ tự (4-6 số; biển 2 dòng
# có thêm 1 số phụ sau chữ cái seri nên dài hơn khi nối 2 dòng lại).
PLATE_PATTERN = re.compile(r"^\d{2}[A-Z]{1,2}\d{4,6}$")


def is_valid_plate(text: str) -> bool:
    """Chuỗi có khớp định dạng biển số VN hay không, tính cả seri 2 chữ cái."""
    return bool(PLATE_PATTERN.match(text))

ASPECT_2ROW_THRESHOLD = 2.0  # width/height < ngưỡng này coi là biển 2 dòng


def deskew(image_bgr: np.ndarray) -> np.ndarray:
    """Chỉnh nghiêng crop biển số bằng minAreaRect trên đường viền lớn nhất.

    An toàn khi không tìm được đường viền đáng tin (ảnh quá nhỏ/nhiễu) hoặc
    góc nghiêng không đáng kể (< 1 độ): trả về ảnh gốc, không xoay.
    """
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    _, mask = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return image_bgr
    largest = max(contours, key=cv2.contourArea)
    if cv2.contourArea(largest) < 0.3 * mask.size:
        return image_bgr

    angle = cv2.minAreaRect(largest)[-1]
    if angle < -45:
        angle += 90
    if abs(angle) < 1.0:
        return image_bgr

    h, w = image_bgr.shape[:2]
    rot_matrix = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
    return cv2.warpAffine(image_bgr, rot_matrix, (w, h),
                          flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)


def order_corners(corners: np.ndarray) -> np.ndarray:
    """Sắp 4 góc theo thứ tự vòng, bắt đầu từ góc trên-trái.

    Sắp theo góc quay quanh tâm tứ giác. Cách thường gặp là chọn góc theo
    tổng/hiệu toạ độ (trên-trái có x+y nhỏ nhất...), nhưng cách đó chọn trùng
    điểm khi biển nghiêng gần 45 độ, làm ma trận biến đổi suy biến và ảnh nắn
    ra bị trống. Sắp theo góc quay luôn cho đủ 4 điểm phân biệt với tứ giác lồi.
    """
    pts = np.asarray(corners, dtype=np.float32).reshape(4, 2)
    centroid = pts.mean(axis=0)
    angles = np.arctan2(pts[:, 1] - centroid[1], pts[:, 0] - centroid[0])
    pts = pts[np.argsort(angles)]
    start = int(np.argmin(pts.sum(axis=1)))  # góc trên-trái làm điểm bắt đầu
    return np.roll(pts, -start, axis=0)


def perspective_correct(image_bgr: np.ndarray, corners: np.ndarray) -> np.ndarray:
    """Nắn biển số về hình chữ nhật phẳng từ 4 góc thật của biển.

    Khác `deskew()` (chỉ xoay được trong mặt phẳng), hàm này khử được cả biến
    dạng phối cảnh khi camera nhìn chéo vào biển. Đây là điều kiện phổ biến ở
    camera bãi giữ xe: camera gắn cao/lệch bên nên hầu như luôn thấy biển ở
    góc nghiêng, không phải chính diện.

    `corners` là 4 điểm (x, y) theo toạ độ pixel của ảnh gốc, lấy từ nhãn
    polygon hoặc từ đầu ra segmentation của model phát hiện biển.
    """
    src = order_corners(corners)
    # Tứ giác suy biến (2 góc trùng nhau) sẽ cho ma trận biến đổi hỏng và ảnh
    # nắn ra trống trơn, nên lùi về ảnh gốc thay vì nắn
    if len(np.unique(np.round(src, 1), axis=0)) < 4:
        return image_bgr

    (tl, tr, br, bl) = src
    width = int(max(np.linalg.norm(tr - tl), np.linalg.norm(br - bl)))
    height = int(max(np.linalg.norm(bl - tl), np.linalg.norm(br - tr)))
    if width < 4 or height < 4:
        return image_bgr

    dst = np.array([[0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1]],
                   dtype=np.float32)
    matrix = cv2.getPerspectiveTransform(src, dst)
    return cv2.warpPerspective(image_bgr, matrix, (width, height), flags=cv2.INTER_CUBIC)


def is_two_row(image_bgr: np.ndarray) -> bool:
    h, w = image_bgr.shape[:2]
    return (w / h) < ASPECT_2ROW_THRESHOLD


def split_rows(image_bgr: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Tách biển 2 dòng thành (dòng trên, dòng dưới) theo điểm trũng nhất của
    histogram chiếu ngang (projection profile) trong dải 30-70% chiều cao,
    tránh tách nhầm ở sát mép trên/dưới."""
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    _, mask = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    profile = mask.sum(axis=1).astype(float)

    h = len(profile)
    lo, hi = int(h * 0.3), int(h * 0.7)
    split_at = lo + int(np.argmin(profile[lo:hi])) if hi > lo else h // 2
    return image_bgr[:split_at], image_bgr[split_at:]


def preprocess_for_ocr(image_bgr: np.ndarray, target_height: int = 48) -> np.ndarray:
    """Đưa crop về chiều cao chuẩn trước khi OCR. Phần lớn crop biển số thật
    trong dữ liệu thu thập được rất nhỏ (trung vị ~46x30px), cần phóng to
    (upscale, nội suy bicubic) chứ không chỉ resize xuống."""
    h, w = image_bgr.shape[:2]
    if h == 0 or w == 0:
        return image_bgr
    scale = target_height / h
    new_w = max(1, round(w * scale))
    interp = cv2.INTER_CUBIC if scale > 1 else cv2.INTER_AREA
    return cv2.resize(image_bgr, (new_w, target_height), interpolation=interp)


def normalize_plate_text(raw_chars: str) -> tuple[str, bool]:
    """Chuẩn hoá chuỗi ký tự thô đọc được thành chuỗi biển số, sửa nhầm lẫn
    OCR theo vị trí kỳ vọng (số/chữ), rồi kiểm tra khớp định dạng biển VN.

    Trả về (chuỗi_đã_chuẩn_hoá, có_hợp_lệ). Chuỗi trả về luôn được giữ lại kể
    cả khi không hợp lệ, để nơi gọi tự quyết định (vd. vẫn hiển thị nhưng gắn
    cờ độ tin cậy thấp) thay vì mất trắng kết quả.
    """
    chars = re.sub(r"[^A-Z0-9]", "", raw_chars.upper())
    if len(chars) < 3:
        return chars, False

    # Seri có thể là 1 hoặc 2 chữ cái (từ 01/01/2025 biển xe máy dùng seri 2
    # chữ cái theo Thông tư 79/2024/TT-BCA). Nếu vị trí 3 đọc ra là chữ cái thì
    # coi đó là seri 2 chữ, không "sửa" nó thành chữ số.
    letter_positions = {2}
    if len(chars) > 3 and chars[3].isalpha():
        letter_positions.add(3)

    out = list(chars)
    for i, c in enumerate(out):
        if i in letter_positions:
            if c.isdigit():
                out[i] = LETTER_POSITION_CONFUSION.get(c, c)
        elif c.isalpha():  # vị trí số (mã tỉnh, số thứ tự)
            out[i] = DIGIT_POSITION_CONFUSION.get(c, c)

    normalized = "".join(out)
    return normalized, is_valid_plate(normalized)


def format_display(normalized: str, head_len: int | None = None) -> str:
    """Định dạng hiển thị biển số, ví dụ 51F-590.11, 50LD-044.11, 59F1-075.09.

    `head_len` là độ dài phần đầu (mã tỉnh + seri) khi nơi gọi biết chắc, cụ
    thể là biển 2 dòng: dòng trên chính là phần đầu nên không cần suy đoán.
    Truyền vào thì dùng luôn, vì với chuỗi 8 ký tự việc suy đoán là bất khả:
    `68P27299` vừa có thể là 68P-272.99 vừa có thể là 68P2-7299, cả hai đều
    hợp lệ, chỉ bố cục ảnh gốc mới phân biệt được.

    Khi không có `head_len`, suy đoán theo thứ tự:
      - Vị trí 3 là chữ cái -> seri 2 chữ cái (50LD, 60AA), phần đầu 4 ký tự.
      - Còn lại 6 chữ số    -> seri có thêm 1 số phụ (59F1), phần đầu 4 ký tự,
                               vì số thứ tự biển VN nhiều nhất chỉ 5 chữ số.
      - Ngược lại           -> seri 1 chữ cái, phần đầu 3 ký tự.

    Chuỗi không khớp định dạng được trả về nguyên văn, không đoán cách chia nhóm.
    """
    if not is_valid_plate(normalized):
        return normalized

    if head_len is None or not (3 <= head_len <= 4 and 4 <= len(normalized) - head_len <= 5):
        # Không có gợi ý tin cậy từ bố cục thì suy đoán
        head_len = 4 if (normalized[3].isalpha() or len(normalized) - 3 == 6) else 3

    head, digits = normalized[:head_len], normalized[head_len:]
    if len(digits) == 5:
        return f"{head}-{digits[:3]}.{digits[3:]}"
    return f"{head}-{digits}"


def char_error_rate(pred: str, gold: str) -> float:
    """Tỉ lệ lỗi ký tự = Levenshtein(pred, gold) / len(gold). gold rỗng trả 0
    nếu pred cũng rỗng, ngược lại 1 (toàn bộ là lỗi)."""
    if not gold:
        return 0.0 if not pred else 1.0
    n, m = len(pred), len(gold)
    dp = list(range(m + 1))
    for i in range(1, n + 1):
        prev, dp[0] = dp[0], i
        for j in range(1, m + 1):
            cur = dp[j]
            cost = 0 if pred[i - 1] == gold[j - 1] else 1
            dp[j] = min(dp[j] + 1, dp[j - 1] + 1, prev + cost)
            prev = cur
    return dp[m] / m


@dataclass
class PlateReading:
    text_raw: str          # chuỗi ghép trực tiếp từ OCR, chưa chuẩn hoá
    text_normalized: str   # đã sửa nhầm lẫn theo vị trí
    text_display: str      # định dạng NNX-NNN.NN để hiển thị
    valid_format: bool
    confidence: float      # min confidence của các dòng đã OCR


def read_plate(crop_bgr: np.ndarray, recognizer, layout: str | None = None,
               corners: np.ndarray | None = None) -> PlateReading:
    """Đọc 1 crop biển số bằng 1 recognizer bất kỳ (cùng interface
    `recognize(image_bgr) -> (text, confidence)`).

    `layout` là `bien_1hang`/`bien_2hang` lấy từ class do PlateDetector của
    Đức xuất ra; nếu không có (vd. đang chạy trên dữ liệu OCR thuần không đi
    qua detector), tự suy ra từ tỉ lệ khung ảnh qua `is_two_row()`.

    `corners` là 4 góc thật của biển trong ảnh truyền vào. Có `corners` thì
    dùng phép nắn phối cảnh (khử được góc nhìn chéo của camera bãi xe); không
    có thì lùi về `deskew()` chỉ xoay được trong mặt phẳng.
    """
    crop = perspective_correct(crop_bgr, corners) if corners is not None else deskew(crop_bgr)
    two_row = (layout == "bien_2hang") if layout else is_two_row(crop)

    head_len = None
    if two_row:
        top, bottom = split_rows(crop)
        text_top, conf_top = recognizer.recognize(preprocess_for_ocr(top))
        text_bottom, conf_bottom = recognizer.recognize(preprocess_for_ocr(bottom))
        raw = text_top + text_bottom
        confidence = min(conf_top, conf_bottom)
        # Dòng trên của biển 2 dòng chính là mã tỉnh + seri, nên độ dài của nó
        # cho biết chỗ ngắt khi hiển thị mà không phải suy đoán
        head_len = len(re.sub(r"[^A-Z0-9]", "", text_top.upper()))
    else:
        raw, confidence = recognizer.recognize(preprocess_for_ocr(crop))

    normalized, valid = normalize_plate_text(raw)
    return PlateReading(raw, normalized, format_display(normalized, head_len), valid, confidence)


class RapidOCRRecognizer:
    """OCR bằng model PP-OCRv3 nhận dạng (rec) chạy qua ONNX Runtime thuần,
    không cần paddlepaddle; engine nhẹ nhất trong 3 lựa chọn, phù hợp thiết
    bị biên cấu hình thấp. Model mặc định huấn luyện cho văn bản đa ngôn ngữ
    (gồm tiếng Trung), không tối ưu riêng cho biển số VN, dùng làm baseline."""

    def __init__(self):
        from rapidocr_onnxruntime import RapidOCR
        self._engine = RapidOCR()
        self._recognizer = self._engine.text_recognizer

    def recognize(self, image_bgr: np.ndarray) -> tuple[str, float]:
        result, _ = self._recognizer([image_bgr])
        if not result or not result[0][0]:
            return "", 0.0
        text, conf = result[0]
        return text, float(conf)


class EasyOCRRecognizer:
    """OCR bằng EasyOCR (CRNN nền PyTorch, dictionary tiếng Anh): charset
    hợp với biển số VN hơn RapidOCR mặc định, nhưng model nặng hơn nhiều
    (PyTorch, không tối ưu ONNX sẵn), ít phù hợp thiết bị biên cấu hình thấp."""

    def __init__(self, gpu: bool = False):
        import easyocr
        self._reader = easyocr.Reader(["en"], gpu=gpu, verbose=False)

    def recognize(self, image_bgr: np.ndarray) -> tuple[str, float]:
        results = self._reader.readtext(image_bgr, detail=1, paragraph=False)
        if not results:
            return "", 0.0
        results.sort(key=lambda r: r[0][0][0])  # theo toạ độ x trái-phải
        text = "".join(r[1] for r in results)
        confidence = min(r[2] for r in results)
        return text, float(confidence)


class CRNNRecognizer:
    """OCR bằng CRNN nhỏ tự huấn luyện riêng cho charset biển số VN (xem
    `src/ml/training/ocr_model.py`, huấn luyện bởi `src/ml/train_ocr_crnn.py`).
    Chỉ đọc 1 dòng ký tự mỗi lần gọi; `read_plate()` tự tách dòng trước khi
    gọi recognizer cho biển 2 dòng, giống 2 recognizer pretrained ở trên."""

    def __init__(self, checkpoint_path, device: str = "cpu"):
        import sys
        from pathlib import Path as _Path

        import torch

        training_dir = str(_Path(__file__).resolve().parents[1] / "training")
        if training_dir not in sys.path:
            sys.path.insert(0, training_dir)
        from ocr_model import CRNN, IMG_HEIGHT, IMG_WIDTH, decode_greedy

        self._torch = torch
        self._device = device
        self._img_height, self._img_width = IMG_HEIGHT, IMG_WIDTH
        self._decode_greedy = decode_greedy

        ckpt = torch.load(checkpoint_path, map_location=device)
        self._model = CRNN().to(device)
        self._model.load_state_dict(ckpt["model_state"])
        self._model.eval()

    def recognize(self, image_bgr: np.ndarray) -> tuple[str, float]:
        img = cv2.resize(image_bgr, (self._img_width, self._img_height), interpolation=cv2.INTER_LINEAR)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0
        tensor = self._torch.from_numpy(gray).unsqueeze(0).unsqueeze(0).to(self._device)  # (1,1,H,W)
        with self._torch.no_grad():
            logits = self._model(tensor)
            probs = self._torch.softmax(logits, dim=2)
            confidence = probs.max(dim=2).values.mean().item()
            text = self._decode_greedy(logits)[0]
        return text, float(confidence)
