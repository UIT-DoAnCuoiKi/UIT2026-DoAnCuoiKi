"""Tổng hợp lượt đo 50 ảnh cổng thật trên Raspberry Pi 5 (run_pi_anh_that.sh).

Ba việc:
1. Thời gian: trung vị, phân vị 90 trên từng ảnh (mỗi ảnh đã lấy trung vị các vòng).
2. Điện năng: trong mốc của mỗi cấu hình chỉ có vòng gọi run(), nên
       E mỗi lượt = (P trung bình trong mốc × độ dài mốc) / số lượt
       E tăng thêm = ((P trung bình trong mốc - P nghỉ) × độ dài mốc) / số lượt
   P nghỉ = trung vị các mẫu trong hai lần nghỉ 60 giây. Công suất đọc từ PMIC nên là
   cận dưới của điện năng ở ổ cắm.
3. Kết quả nhận dạng: so từng ảnh (chuỗi biển, loại xe, kiểu dáng) với lượt đo cùng cấu
   hình trên máy dev (experiments/anh_that_dev/<cấu hình>_4luong.csv).

Chạy trên máy dev sau khi chép experiments/pi5_anh_that về:
    python src/ml/summarize_pi_anh_that.py
"""
from __future__ import annotations

import csv
import statistics
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

EXP = Path(__file__).resolve().parent / "experiments"
PI = EXP / "pi5_anh_that"
DEV = EXP / "anh_that_dev"


def doc_csv(p: Path) -> list[dict]:
    with open(p, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def phan_vi(x: list[float], q: float) -> float:
    s = sorted(x)
    k = (len(s) - 1) * q
    lo, hi = int(k), min(int(k) + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


def main() -> None:
    dien = doc_csv(PI / "nhat_ky_dien.csv")
    moc = {r["nhan"]: (float(r["t_bat_dau"]), float(r["t_ket_thuc"])) for r in doc_csv(PI / "moc_thoi_gian.csv")}

    def mau(t0: float, t1: float) -> list[float]:
        return [float(m["p_tong_w"]) for m in dien if t0 <= float(m["t_unix"]) <= t1]

    def dem_co(t0: float, t1: float, mat_na: int) -> int:
        # get_throttled bit 0 sụt áp, bit 1 đang giới hạn xung, bit 2 đang hạ xung, bit 3 chạm ngưỡng nhiệt mềm.
        # Chỉ bit 3 bật mà xung vẫn tối đa thì CPU chưa chạy chậm lại.
        return sum(1 for m in dien if t0 <= float(m["t_unix"]) <= t1 and int(m["throttled"], 16) & mat_na)

    def nhiet_do_min_5_phut_truoc(t0: float) -> float:
        # Script chờ nhiệt độ (phần nguyên) <= 58°C tối đa 5 phút, min trong 5 phút trước cho biết có đạt không
        return min(float(m["nhiet_do_c"]) for m in dien if t0 - 300 <= float(m["t_unix"]) < t0)

    p_nghi = statistics.median(mau(*moc["nghi_truoc"]) + mau(*moc["nghi_sau"]))
    hang = []
    for ten in [k for k in moc if not k.startswith("nghi_")]:
        rows = doc_csv(PI / f"{ten}.csv")
        tv = [float(r["trung_vi_ms"]) for r in rows]
        so_luot = int(dict(l.split("=") for l in (PI / f"{ten}_moc.txt").read_text().split())["so_luot"])
        t0, t1 = moc[ten]
        p = mau(t0, t1)
        p_tb = statistics.mean(p)
        dai = t1 - t0
        ket = {
            "cau_hinh": ten, "so_anh": len(rows), "so_luot": so_luot,
            "trung_vi_ms": round(statistics.median(tv), 1), "p90_ms": round(phan_vi(tv, 0.9), 1),
            "trung_vi_o_to_ms": round(statistics.median(float(r["trung_vi_ms"]) for r in rows if r["nhom"] == "o_to"), 1),
            "trung_vi_xe_may_ms": round(statistics.median(float(r["trung_vi_ms"]) for r in rows if r["nhom"] == "xe_may"), 1),
            "so_anh_chay_kieu_dang": sum(1 for r in rows if r["kieu_dang"]),
            "giay_do": round(dai, 1), "so_mau_dien": len(p),
            "giay_tu_moc_truoc": round(t0 - max(t for _, t in moc.values() if t <= t0), 1),
            "nhiet_do_min_5_phut_truoc_c": nhiet_do_min_5_phut_truoc(t0),
            "nhiet_do_max_c": max(float(m["nhiet_do_c"]) for m in dien if t0 <= float(m["t_unix"]) <= t1),
            "so_mau_sut_ap_ha_xung": dem_co(t0, t1, 0x7), "so_mau_nhiet_mem": dem_co(t0, t1, 0x8),
            "xung_min_mhz": min(float(m["xung_mhz"]) for m in dien if t0 <= float(m["t_unix"]) <= t1),
            "p_tb_w": round(p_tb, 3), "p_nghi_w": round(p_nghi, 3),
            "e_moi_luot_j": round(p_tb * dai / so_luot, 3),
            "e_tang_them_j": round((p_tb - p_nghi) * dai / so_luot, 3),
        }
        dev_p = DEV / f"{ten}_4luong.csv"
        if dev_p.exists():
            dev = {r["anh"]: r for r in doc_csv(dev_p)}
            for truong in ("bien", "loai_xe", "kieu_dang"):
                ket[f"khop_dev_{truong}"] = sum(1 for r in rows if dev.get(r["anh"], {}).get(truong) == r[truong])
        hang.append(ket)

    with open(PI / "tong_hop.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(hang[0]))
        w.writeheader()
        w.writerows(hang)
    for k in hang:
        print(k)
    print(f"\nĐã ghi {PI / 'tong_hop.csv'}")


if __name__ == "__main__":
    main()
