"""Nhãn chuỗi ký tự cho tập test vn_plate, gán bằng mắt.

Quy trình gán: `prepare_vnplate_testset.py` cắt 100 biển ngẫu nhiên (seed 2026)
và xuất thành lưới ảnh không kèm bất kỳ dự đoán nào của model. Người gán đọc
ảnh và ghi lại chuỗi nhìn thấy. Cách làm này giữ nhãn độc lập với model đang
đánh giá; nếu điền sẵn dự đoán rồi sửa thì kết quả đánh giá sẽ bị thổi phồng.

Biển không đọc được chắc chắn bằng mắt (mờ, bạc màu, bị cắt) được gán None và
loại khỏi tập test, không đoán. Tỉ lệ này tự nó là một số liệu về chất lượng
dữ liệu nên vẫn được ghi lại.

Chạy: .venv/Scripts/python.exe src/ml/data_prep/vnplate_test_labels.py
"""

from __future__ import annotations

import csv
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
MANIFEST = REPO_ROOT / "data" / "processed" / "vn-plate-test-manifest.csv"
OUT_CSV = REPO_ROOT / "data" / "processed" / "vn-plate-test.csv"

# index -> chuỗi biển đọc được. None nghĩa là không đọc được chắc chắn.
LABELS: dict[int, str | None] = {
    0: "51F59011", 1: "51F24403", 2: "51A01204", 3: "51F61712", 4: "47D117237",
    5: "51F31118", 6: "51A02923", 7: "59F107509", 8: "51F32488", 9: "51G31691",
    10: "64D113241", 11: "60B736638", 12: "59K140650", 13: "68P27299", 14: "83H96050",
    15: "59F168955", 16: None, 17: "59F113860", 18: "51F22261", 19: "64F81149",
    20: "51F15585", 21: "68H75764", 22: "51G49539", 23: "54U52813", 24: "85D101611",
    25: "59E121500", 26: "67E11922", 27: "65P79679", 28: "51G37675", 29: None,
    30: "65X37533", 31: "51F79512", 32: None, 33: "59F170424", 34: "51G10096",
    35: "68F26766", 36: "63V28794", 37: "51A89714", 38: "59L223714", 39: "69F68587",
    40: "51A77529", 41: "94E101304", 42: "59F147488", 43: "51F74776", 44: "51F22261",
    45: "67C105355", 46: "51G51008", 47: "51F07973", 48: "51F22029", 49: "51F07973",
    50: "51L73998", 51: "51F89357", 52: None, 53: "29A51796", 54: "59C116274",
    55: "51A96141", 56: "94E102209", 57: "59S159484", 58: "59H154986", 59: "51F63034",
    60: "63Y10200", 61: "59S247831", 62: "51G39466", 63: "51G50553", 64: "51G21797",
    65: "55P56876", 66: "65U19111", 67: "59F138151", 68: "64L14012", 69: "59E103640",
    70: "83S45372", 71: "51G10096", 72: "68P27299", 73: "51F73029", 74: "51G22237",
    75: "51F24476", 76: "50LD04411", 77: "68M39934", 78: "51F59881", 79: "65F13556",
    80: "65X45189", 81: "51A16598", 82: "51G49539", 83: "65D104017", 84: "66P15739",
    85: "67F111317", 86: "51A96141", 87: "59T192270", 88: "59P220947", 89: "51G51332",
    90: "60A39951", 91: "59S216555", 92: "51F06532", 93: "51F63034", 94: "51G51292",
    95: "64B120263", 96: "66L105273", 97: "94H31450", 98: "61A22959", 99: "51A69172",
}

# Biển seri đặc biệt 2 chữ cái (LD, DA...) không khớp regex biển thường
# (`\d{2}[A-Z]\d{4,6}`). Giữ trong tập test vì đây là biển thật gặp ngoài đời,
# nhưng đánh dấu để phân tích riêng.
SPECIAL_SERIES_INDICES = {76}


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
                "source": "vn_plate",
                "special_series": idx in SPECIAL_SERIES_INDICES,
            })

    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    total = len(rows) + n_unreadable
    n_1h = sum(1 for r in rows if r["layout"] == "bien_1hang")
    print(f"Đã gán nhãn {len(rows)}/{total} biển "
          f"({n_unreadable} biển không đọc được bằng mắt, {n_unreadable / total:.1%})")
    print(f"  biển 1 dòng: {n_1h}, biển 2 dòng: {len(rows) - n_1h}")
    print(f"  biển seri đặc biệt (LD/DA): {sum(r['special_series'] for r in rows)}")
    print(f"Đã ghi {OUT_CSV.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
