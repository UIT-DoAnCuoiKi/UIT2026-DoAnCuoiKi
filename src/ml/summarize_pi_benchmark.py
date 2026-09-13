"""Ghép log thời gian và log điện năng của Raspberry Pi 5 thành bảng tổng hợp.

Đầu vào (do run_pi_benchmark.sh sinh ra, mặc định trong src/ml/experiments/pi5/):
    bench_<nhánh>_<n>luong.log        kết quả benchmark_pipeline.py từng cấu hình
    tai_lien_tuc_<nhánh>_4luong.log   loạt 60 lượt liên tục
    nhat_ky_dien.csv                  mẫu công suất/nhiệt độ mỗi giây
    moc_thoi_gian.csv                 mốc bắt đầu, kết thúc, nhiệt độ lúc bắt đầu từng loạt

CÁCH TÍNH:

  Công suất của một loạt = TRUNG VỊ các mẫu có t_unix nằm trong mốc của loạt đó.
  Dùng trung vị vì lúc nạp model và lúc kết thúc có vài mẫu vọt lên hoặc tụt
  xuống, trung bình bị chúng kéo lệch.

  Đường nền P_nghỉ = trung vị hai loạt `nghi_truoc` và `nghi_sau` gộp lại. Đo cả
  đầu và cuối buổi để thấy máy có trôi không.

  Điện năng một lượt xe, báo hai con số vì chúng trả lời hai câu hỏi khác nhau:
      E_toàn_phần = P_tải × t_suy_luận             (Pi tiêu bao nhiêu khi xử lý 1 xe)
      E_tăng_thêm = (P_tải - P_nghỉ) × t_suy_luận  (riêng phần do suy luận gây ra)
  Đơn vị jun (J = W × s). P_tải chỉ đáng tin ở loạt tải liên tục: loạt ngắn có xen
  thời gian nạp model và đo từng model riêng nên công suất bị pha loãng.

  Điều kiện hợp lệ: bit 0-3 của `throttled` phải bằng 0 ở mọi mẫu, tức cột
  `throttled_hien_tai` là 0x0. Bit 0-3 là trạng thái lúc lấy mẫu; khác 0 là Pi
  đang hạ xung vì nóng hoặc sụt áp, số thời gian của loạt đó phải xem lại.
  Bit 16-19 là cờ dính "đã từng xảy ra từ lúc khởi động", chỉ xoá khi reboot,
  nên không dùng để xét một loạt cụ thể.

Chạy (trên máy dev, sau khi đã chép thư mục kết quả về):
    python src/ml/summarize_pi_benchmark.py
    python src/ml/summarize_pi_benchmark.py --thu-muc src/ml/experiments/pi5_lan1_khong_cho_nguoi
"""

from __future__ import annotations

import argparse
import csv
import math
import re
import statistics
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

MAC_DINH = Path(__file__).resolve().parent / "experiments" / "pi5"

RE_LUONG = re.compile(r"ML_INTRAOP_THREADS = (\d+)")
RE_LUOT_DAU = re.compile(r"Lượt đầu tiên.*?:\s*([\d.]+) ms")
RE_TRUNG_VI = re.compile(r"Sau khi làm nóng, trung vị\s*:\s*([\d.]+) ms\s*\(min ([\d.]+), max ([\d.]+)\)")
RE_CPU_TIME = re.compile(r"CPU-time trung vị.*?:\s*([\d.]+) ms")
RE_TI_SO = re.compile(r"Số luồng dùng trung bình.*?:\s*([\d.]+)")
RE_SO_BIEN = re.compile(r"Số biển phát hiện được trên ảnh này: (\d+)")
# Có từ bản benchmark_pipeline.py đọc ML_COARSE_WEIGHTS/ML_STYLE_ONNX; log cũ không có
RE_DINH_VI = re.compile(r"Định vị xe\s*:\s*(\S+)")
RE_KIEU_DANG = re.compile(r"Kiểu dáng xe\s*:\s*(\S+)")
RE_CAU_HINH = re.compile(r"^(?:bench|tai_lien_tuc)_(.+)_\d+luong$")
# "  Chuyển màu BGR sang RGB                  1.2ms      1.0     1.5   0.2%"
RE_BUOC = re.compile(r"^  (\S.*?)\s+([\d.]+)ms\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)%$")
# "  Phát hiện biển (YOLOv8n)         [1, 3, 640, 640]     12.2    45.30ms  44.10  46.20"
RE_MODEL = re.compile(r"^  (\S.*?)\s+(\[[^\]]*\])\s+([\d.]+)\s+([\d.]+)ms\s+([\d.]+)\s+([\d.]+)$")


def _so(regex: re.Pattern, text: str, kieu=float):
    m = regex.search(text)
    return kieu(m.group(1)) if m else None


def doc_log(p: Path) -> dict:
    t = p.read_text(encoding="utf-8")
    m_tv = RE_TRUNG_VI.search(t)
    dong = t.splitlines()
    dinh_vi, kieu_dang = _so(RE_DINH_VI, t, str), _so(RE_KIEU_DANG, t, str)
    m_ch = RE_CAU_HINH.match(p.stem)
    return {
        "loat": p.stem,
        "cau_hinh": m_ch.group(1) if m_ch else None,
        "dinh_vi_file": dinh_vi,
        "kieu_dang_file": kieu_dang,
        "luong": _so(RE_LUONG, t, int),
        "nhanh_dinh_vi": ("onnx" if dinh_vi.endswith(".onnx") else "pt") if dinh_vi else "khong_ghi",
        "so_bien_tren_anh": _so(RE_SO_BIEN, t, int),
        "luot_dau_ms": _so(RE_LUOT_DAU, t),
        "trung_vi_ms": float(m_tv.group(1)) if m_tv else None,
        "min_ms": float(m_tv.group(2)) if m_tv else None,
        "max_ms": float(m_tv.group(3)) if m_tv else None,
        "cpu_time_ms": _so(RE_CPU_TIME, t),
        "ti_so_cpu_wall": _so(RE_TI_SO, t),
        "buoc": [
            {"buoc": m.group(1).strip(), "trung_vi_ms": float(m.group(2)), "min_ms": float(m.group(3)),
             "max_ms": float(m.group(4)), "ti_le_pct": float(m.group(5))}
            for m in map(RE_BUOC.match, dong) if m
        ],
        "model_rieng": [
            {"model": m.group(1).strip(), "dau_vao": m.group(2), "mb": float(m.group(3)),
             "trung_vi_ms": float(m.group(4)), "min_ms": float(m.group(5)), "max_ms": float(m.group(6))}
            for m in map(RE_MODEL.match, dong) if m
        ],
    }


def cua_so(mau: list[dict], t0: float, t1: float) -> list[dict]:
    return [m for m in mau if t0 <= float(m["t_unix"]) <= t1]


def thong_ke_dien(mau_con: list[dict]) -> dict:
    if not mau_con:
        return {}
    p = [float(m["p_tong_w"]) for m in mau_con]
    kq = {
        "so_mau": len(mau_con),
        "p_trung_vi_w": round(statistics.median(p), 3),
        "p_min_w": round(min(p), 3),
        "p_max_w": round(max(p), 3),
        "nhiet_do_max_c": round(max(float(m["nhiet_do_c"]) for m in mau_con), 1),
        "cpu_trung_vi_pct": round(statistics.median(float(m["cpu_pct"]) for m in mau_con), 1),
        # Bit 0-3 là trạng thái lúc lấy mẫu, bit 16-19 là cờ dính "đã từng xảy ra từ lúc khởi động".
        "throttled": ",".join(sorted({m["throttled"] for m in mau_con})),
        "throttled_hien_tai": ",".join(sorted({hex(int(m["throttled"], 16) & 0xF) for m in mau_con})),
    }
    # Lượt 1 chưa ghi tốc độ quạt
    quat = [float(m["quat_rpm"]) for m in mau_con if m.get("quat_rpm") not in (None, "", "nan")]
    kq["quat_rpm_max"] = round(max(quat)) if quat and not math.isnan(max(quat)) else None
    return kq


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--thu-muc", type=Path, default=MAC_DINH, help="thư mục kết quả của một lần chạy")
    thu_muc: Path = ap.parse_args().thu_muc

    mau = list(csv.DictReader(open(thu_muc / "nhat_ky_dien.csv", encoding="utf-8")))
    moc = {r["nhan"]: r for r in csv.DictReader(open(thu_muc / "moc_thoi_gian.csv", encoding="utf-8"))}

    def mau_cua(nhan: str) -> list[dict]:
        return cua_so(mau, float(moc[nhan]["t_bat_dau"]), float(moc[nhan]["t_ket_thuc"]))

    def thong_tin_moc(nhan: str) -> dict:
        # Lượt 1 chưa có hai cột này
        return {"nhiet_do_bat_dau_c": moc[nhan].get("nhiet_do_bat_dau_c"),
                "giay_cho_nguoi": moc[nhan].get("giay_cho_nguoi")}

    logs = {p.stem: doc_log(p) for p in sorted(thu_muc.glob("*.log"))}

    nghi = thong_ke_dien(mau_cua("nghi_truoc") + mau_cua("nghi_sau"))
    p_nghi = nghi["p_trung_vi_w"]

    hang = [{"loat": n, **thong_tin_moc(n), **thong_ke_dien(mau_cua(n))} for n in ("nghi_truoc", "nghi_sau")]
    for ten, d in logs.items():
        if ten not in moc:
            print(f"  [bỏ qua] không có mốc thời gian cho {ten}")
            continue
        e = thong_ke_dien(mau_cua(ten))
        r = {k: v for k, v in d.items() if k not in ("buoc", "model_rieng")}
        r.update(e)
        r.update(thong_tin_moc(ten))
        r["lien_tuc"] = ten.startswith("tai_lien_tuc")
        if d["trung_vi_ms"] and e:
            t_s = d["trung_vi_ms"] / 1000.0
            r["e_toan_phan_j"] = round(e["p_trung_vi_w"] * t_s, 3)
            r["e_tang_them_j"] = round((e["p_trung_vi_w"] - p_nghi) * t_s, 3)
        hang.append(r)

    cot = ["loat", "cau_hinh", "dinh_vi_file", "kieu_dang_file", "nhanh_dinh_vi", "luong", "lien_tuc", "trung_vi_ms", "min_ms", "max_ms",
           "luot_dau_ms", "cpu_time_ms", "ti_so_cpu_wall", "p_trung_vi_w", "p_min_w", "p_max_w",
           "e_toan_phan_j", "e_tang_them_j", "nhiet_do_bat_dau_c", "nhiet_do_max_c", "giay_cho_nguoi",
           "quat_rpm_max", "cpu_trung_vi_pct", "throttled", "throttled_hien_tai", "so_mau", "so_bien_tren_anh"]
    with open(thu_muc / "tong_hop.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cot, extrasaction="ignore")
        w.writeheader()
        w.writerows(hang)

    with open(thu_muc / "tung_buoc.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["loat", "cau_hinh", "nhanh_dinh_vi", "luong", "buoc", "trung_vi_ms",
                                          "min_ms", "max_ms", "ti_le_pct"])
        w.writeheader()
        for ten, d in logs.items():
            for b in d["buoc"]:
                w.writerow({"loat": ten, "cau_hinh": d["cau_hinh"], "nhanh_dinh_vi": d["nhanh_dinh_vi"], "luong": d["luong"], **b})

    with open(thu_muc / "model_rieng.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["loat", "cau_hinh", "luong", "model", "dau_vao", "mb", "trung_vi_ms",
                                          "min_ms", "max_ms"])
        w.writeheader()
        for ten, d in logs.items():
            for m in d["model_rieng"]:
                w.writerow({"loat": ten, "cau_hinh": d["cau_hinh"], "luong": d["luong"], **m})

    print(f"Đường nền lúc nghỉ: {p_nghi} W (đầu buổi {hang[0]['p_trung_vi_w']} W, "
          f"cuối buổi {hang[1]['p_trung_vi_w']} W)")
    print()
    print(f"{'Loạt':28s} {'Trung vị':>9s} {'CPU/wall':>9s} {'Công suất':>10s} {'E/xe':>8s} "
          f"{'Nhiệt đầu':>9s} {'Nhiệt max':>9s}  throttled")
    for r in hang[2:]:
        print(f"{r['loat']:28s} {r['trung_vi_ms'] or 0:8.1f}ms {r['ti_so_cpu_wall'] or 0:9.2f} "
              f"{r.get('p_trung_vi_w', 0):9.2f}W {r.get('e_toan_phan_j', 0):7.2f}J "
              f"{str(r.get('nhiet_do_bat_dau_c') or '?'):>8s}° {r.get('nhiet_do_max_c', 0):8.1f}°  "
              f"{r.get('throttled_hien_tai', '?')} (cờ dính: {r.get('throttled', '?')})")
    print(f"\nĐã ghi tong_hop.csv, tung_buoc.csv, model_rieng.csv trong {thu_muc}")


if __name__ == "__main__":
    main()
