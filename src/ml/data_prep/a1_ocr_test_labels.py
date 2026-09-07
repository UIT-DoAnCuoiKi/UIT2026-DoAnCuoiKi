"""Nhãn chuỗi ký tự cho tập test A1, gán bằng mắt.

Quy trình gán: `prepare_a1_ocr_testset.py` cắt 200 biển cân bằng layout (seed
2026) và xuất thành 20 lưới ảnh không kèm bất kỳ dự đoán nào của model. Đọc
từng ảnh và ghi lại chuỗi nhìn thấy TRƯỚC khi chạy OCR — giữ nhãn độc lập với
model đang đánh giá, đúng nguyên tắc đã áp dụng cho `vn_plate`
(`vnplate_test_labels.py`); nếu điền sẵn dự đoán rồi sửa thì đánh giá thành
vòng tròn logic, accuracy bị thổi phồng.

Biển không đọc được chắc chắn bằng mắt (mờ, bị cắt/che mất ký tự, hoặc ảnh cắt
bị hỏng do polygon suy biến lúc nắn phối cảnh) được gán None và loại khỏi tập
test, không đoán. Một vài trường hợp gán None cụ thể đáng chú ý:
  - #023: nhãn gốc A1 gán layout bien_1hang nhưng ảnh thực tế là biển 2 dòng
    (71-C2 / 635.10) — lỗi nhãn nguồn, không dùng được vì layout sai sẽ khiến
    OCR tách dòng sai không do lỗi model.
  - #054, #068, #090, #115, #116, #144, #155: ảnh cắt hỏng (polygon gần suy
    biến khiến `perspective_correct` cho ra ảnh kéo giãn dị dạng, không còn
    là biển số) — lỗi kỹ thuật của bước cắt, không phải biển mờ tự nhiên.
  - Vài cặp chỉ số cho cùng 1 biển (A1 có ảnh lặp, vd #007/#034/#067 cùng là
    "51G-513.32") được dùng để đối chiếu chéo giữa các nhãn đã gán khi 1 ảnh
    mờ hơn ảnh còn lại — không phải đối chiếu với dự đoán model nên không vi
    phạm nguyên tắc chống vòng lặp logic.

Chạy: .venv/Scripts/python.exe src/ml/data_prep/a1_ocr_test_labels.py
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":  # console Windows mặc định cp1252
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

REPO_ROOT = Path(__file__).resolve().parents[3]
MANIFEST = REPO_ROOT / "data" / "processed" / "a1-ocr-test-manifest.csv"
OUT_CSV = REPO_ROOT / "data" / "processed" / "a1-ocr-test.csv"

# index -> chuỗi biển đọc được (đã chuẩn hoá, không dấu ngăn cách). None nghĩa
# là không đọc được chắc chắn hoặc ảnh/nhãn nguồn có vấn đề (xem docstring).
LABELS: dict[int, str | None] = {
    # --- bien_1hang (0-99) ---
    0: "51F07973", 1: "30A44035", 2: "51F63034", 3: "51A72078", 4: "51A05227",
    5: "88A23016", 6: "14A25074", 7: "51G51332", 8: "51F07122", 9: "30V3993",
    10: "89A20061", 11: "30A04926", 12: "51G43630", 13: "51B21666", 14: "30G03947",
    15: "51F22029", 16: "51A05227", 17: "29D09566", 18: "30F19643", 19: "89A20664",
    20: "51F44614", 21: "30N4616", 22: "51F59881", 23: None, 24: "51F78904",
    25: "29C81839", 26: "30G40304", 27: "29D09566", 28: "60LD00584", 29: "51F15585",
    30: "30N4616", 31: None, 32: "51F04275", 33: "51F31118", 34: "51G51332",
    35: "51F06948", 36: "51G25481", 37: "51A72078", 38: "30E06618", 39: "51F61712",
    40: "51G25181", 41: "51G39466", 42: "29A29441", 43: "30E86044", 44: "51F04877",
    45: "36A04104", 46: "29C73587", 47: "51F24476", 48: "30A57599", 49: "51G29034",
    50: "51D41498", 51: "30G11155", 52: "51K27027", 53: "51A89714", 54: None,
    55: "51F04877", 56: "30E61035", 57: "51G39466", 58: "51F16159", 59: "51G31691",
    60: "51F59881", 61: "89A19640", 62: "51G37307", 63: "51D10039", 64: "52Y6490",
    65: "51H47216", 66: "51G51008", 67: "51G51332", 68: None, 69: "51F92401",
    70: "51F22261", 71: "30A23451", 72: "51F58214", 73: "51A72444", 74: "29D21596",
    75: "51F63034", 76: "51G51332", 77: "51F73029", 78: "48A05177", 79: "51A02923",
    80: "51G22237", 81: "51F35613", 82: "51F61712", 83: "29D09566", 84: "61N9396",
    85: "51A05227", 86: "51F02687", 87: "51F61712", 88: "30F99015", 89: "51G01177",
    90: None, 91: "30E38721", 92: "51G37307", 93: "51G10096", 94: "30G36336",
    95: "51F24403", 96: None, 97: "51A05227", 98: "30F97025", 99: "30F26449",
    # --- bien_2hang (100-199) ---
    100: "52U78693", 101: "30F11292", 102: None, 103: None, 104: None,
    105: "79N296995", 106: "59S241737", 107: "59X163066", 108: "59H146828", 109: "55P44641",
    110: None, 111: "59B138559", 112: None, 113: "69C120591", 114: "59Z120681",
    115: None, 116: None, 117: "79H58812", 118: "77C103188", 119: None,
    120: "60B598364", 121: "99A08487", 122: None, 123: "59X318737", 124: "51V44579",
    125: "63B140991", 126: "59S228834", 127: "51C77737", 128: "55P92840", 129: "22H51198",
    130: None, 131: None, 132: "59F173270", 133: "59C228114", 134: "30A52186",
    135: "30G37213", 136: None, 137: "59S194422", 138: "84H00889", 139: "59X139458",
    140: "59S229969", 141: "59E170535", 142: "95B136160", 143: "59X267178", 144: None,
    145: "30F65946", 146: "59M107790", 147: "72C136130", 148: "66P151993", 149: "72A63235",
    150: "52F73840", 151: "59M160886", 152: "67CT61134", 153: "62P153221", 154: None,
    155: None, 156: "51K36443", 157: "51F18535", 158: None, 159: "59U111444",
    160: "59C143017", 161: "30F26449", 162: "51G30126", 163: "59N174939", 164: "89A04369",
    165: "30G06534", 166: "81B126810", 167: "30G59068", 168: "68G151270", 169: "51U83423",
    170: None, 171: "71H71632", 172: "59U193221", 173: "67M136037", 174: None,
    175: "59M197372", 176: "59P147969", 177: "51G30126", 178: None, 179: "93F124985",
    180: "36A25649", 181: "54T40987", 182: "61A63261", 183: None, 184: "30E77408",
    185: "59X188265", 186: None, 187: "54F37071", 188: "59F103055", 189: "59V267157",
    190: "30E34441", 191: "54U39055", 192: "59F145842", 193: "29D08722", 194: "30A05857",
    195: None, 196: "59L213938", 197: "30F19643", 198: "59T164417", 199: "51G49855",
}

# Series 2 chữ cái đặc biệt (LD, DA...) không khớp regex biển thường
# (`\d{2}[A-Z]\d{4,6}`). Giữ trong tập test vì đây là biển thật gặp ngoài đời,
# nhưng đánh dấu để phân tích riêng — cùng quy ước với vnplate_test_labels.py.
SPECIAL_SERIES_INDICES = {28}


def main() -> None:
    rows = []
    n_unreadable = 0
    with open(MANIFEST, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            idx = int(r["index"])
            label = LABELS.get(idx)
            if label is None:
                n_unreadable += 1
                continue
            rows.append({
                "image_path": r["image_path"],
                "label_raw": label,
                "label_clean": label,
                "layout": r["layout"],
                "width": r["width"],
                "height": r["height"],
                "source": "a1_ocr_test",
                "special_series": idx in SPECIAL_SERIES_INDICES,
            })

    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    total = len(rows) + n_unreadable
    n_1h = sum(1 for r in rows if r["layout"] == "bien_1hang")
    print(f"Đã gán nhãn {len(rows)}/{total} biển "
          f"({n_unreadable} biển loại, {n_unreadable / total:.1%})")
    print(f"  biển 1 dòng: {n_1h}, biển 2 dòng: {len(rows) - n_1h}")
    print(f"  biển seri đặc biệt (LD/DA): {sum(r['special_series'] for r in rows)}")
    print(f"Đã ghi {OUT_CSV.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
