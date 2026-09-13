"""Đo thời gian pipeline trên nhiều ảnh camera cổng thật, thay cho 1 ảnh mẫu.

Vì sao cần: benchmark_pipeline.py đo trên đúng 1 ảnh xe máy có 12 biển. Ảnh cổng thật
thường 1 xe 1 biển, và với xe máy thì pipeline không chạy bước kiểu dáng, nên số đo
đó không đại diện cho lượt xe thật.

Ảnh: 25 ảnh ô tô (carlong_) và 25 ảnh xe máy (greenpack_) lấy từ tập val của
kaggle_vn_plate_segment, đều là camera cổng bãi xe. Chọn ngẫu nhiên với seed cố định,
danh sách lưu ở src/ml/data/anh_cong_benchmark.txt để máy khác đo cùng bộ ảnh.

Cách đo:
  - Nạp hết ảnh vào bộ nhớ trước, không tính thời gian đọc đĩa.
  - Làm nóng bằng vài ảnh đầu, không tính.
  - Mỗi ảnh chạy `OnnxAlprPipeline.run()` N vòng, đồng hồ `time.perf_counter()`,
    lấy trung vị N vòng của ảnh đó. Báo trung vị và phân vị 90 trên 50 ảnh.
  - Ghi mốc unix bắt đầu và kết thúc của vòng đo vào file `_moc.txt`, trong khoảng
    đó chỉ có `run()` chạy, để ghép với log điện năng.
  - Ghi kết quả nhận dạng từng ảnh (số biển, chuỗi biển, loại xe, kiểu dáng) để so
    kết quả giữa hai máy.

Model chọn bằng biến môi trường giống backend: ML_INTRAOP_THREADS, ML_COARSE_WEIGHTS,
ML_STYLE_ONNX. Tên model thật sự chạy được in ở đầu output.

Chạy:
  python src/ml/benchmark_anh_that.py --tao-danh-sach        # chỉ cần 1 lần, trên máy có data/raw
  python src/ml/benchmark_anh_that.py --out ket_qua.csv
"""
from __future__ import annotations

import argparse
import csv
import os
import random
import statistics
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ML_DIR = REPO_ROOT / "src" / "ml"
for _p in (ML_DIR, ML_DIR / "training", ML_DIR / "plate_detection_pipeline", ML_DIR / "plate_color_pipeline"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

THU_MUC_ANH = REPO_ROOT / "data" / "raw" / "kaggle_vn_plate_segment" / "images" / "val"
DANH_SACH = ML_DIR / "data" / "anh_cong_benchmark.txt"
PLATE_WEIGHTS = ML_DIR / "plate_detection_pipeline" / "weights" / "yolov8n_a1_640.onnx"
NHOM = {"carlong_": "o_to", "greenpack_": "xe_may"}


def tao_danh_sach(so_moi_nhom: int, seed: int) -> None:
    rng = random.Random(seed)
    chon = []
    for tien_to in NHOM:
        tat_ca = sorted(p.name for p in THU_MUC_ANH.iterdir() if p.name.startswith(tien_to))
        chon += sorted(rng.sample(tat_ca, so_moi_nhom))
    DANH_SACH.write_text("\n".join(chon) + "\n", encoding="utf-8")
    print(f"Đã ghi {len(chon)} ảnh vào {DANH_SACH.relative_to(REPO_ROOT)} (seed {seed})")


def phan_vi(x: list[float], q: float) -> float:
    s = sorted(x)
    k = (len(s) - 1) * q
    lo, hi = int(k), min(int(k) + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tao-danh-sach", action="store_true")
    ap.add_argument("--so-moi-nhom", type=int, default=25)
    ap.add_argument("--seed", type=int, default=2026)
    ap.add_argument("--so-vong", type=int, default=3)
    ap.add_argument("--lam-nong", type=int, default=3)
    ap.add_argument("--out", type=Path, default=Path("anh_that.csv"))
    args = ap.parse_args()

    if args.tao_danh_sach:
        tao_danh_sach(args.so_moi_nhom, args.seed)
        return

    import cv2

    from pipeline.onnx_pipeline import _DEFAULTS, OnnxAlprPipeline, _intra_op_threads

    coarse = os.environ.get("ML_COARSE_WEIGHTS") or None
    style = os.environ.get("ML_STYLE_ONNX") or None
    ten_anh = [d.strip() for d in DANH_SACH.read_text(encoding="utf-8").splitlines() if d.strip()]
    anh = []
    for ten in ten_anh:
        img = cv2.imread(str(THU_MUC_ANH / ten))
        if img is None:
            raise FileNotFoundError(THU_MUC_ANH / ten)
        anh.append((ten, img))

    print(f"  Định vị xe   : {Path(coarse or _DEFAULTS['coarse_weights']).name}")
    print(f"  Kiểu dáng xe : {Path(style or _DEFAULTS['style_onnx']).name}")
    print(f"  ML_INTRAOP_THREADS = {_intra_op_threads()}")
    print(f"  Số ảnh: {len(anh)}, làm nóng {args.lam_nong} ảnh, đo {args.so_vong} vòng mỗi ảnh")

    pipe = OnnxAlprPipeline(plate_weights=str(PLATE_WEIGHTS), coarse_weights=coarse, style_onnx=style)
    for _, img in anh[: args.lam_nong]:
        pipe.run(img)

    thoi_gian: dict[str, list[float]] = {ten: [] for ten, _ in anh}
    ket_qua: dict[str, dict] = {}
    t_bat_dau = time.time()
    for _ in range(args.so_vong):
        for ten, img in anh:
            t0 = time.perf_counter()
            r = pipe.run(img)
            thoi_gian[ten].append((time.perf_counter() - t0) * 1000)
            ket_qua[ten] = r
    t_ket_thuc = time.time()

    hang = []
    for ten, img in anh:
        r = ket_qua[ten]
        hang.append({
            "anh": ten,
            "nhom": next(v for k, v in NHOM.items() if ten.startswith(k)),
            "rong": img.shape[1], "cao": img.shape[0],
            "so_bien": len(r["plates"]),
            "bien": "|".join(p["plate_text"] or "" for p in r["plates"]),
            "loai_xe": r["vehicle_type"] or "",
            "kieu_dang": r["vehicle_style"] or "",
            **{f"vong_{i + 1}_ms": round(v, 1) for i, v in enumerate(thoi_gian[ten])},
            "trung_vi_ms": round(statistics.median(thoi_gian[ten]), 1),
        })

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(hang[0]))
        w.writeheader()
        w.writerows(hang)
    so_luot = len(anh) * args.so_vong
    args.out.with_name(args.out.stem + "_moc.txt").write_text(
        f"t_bat_dau={t_bat_dau:.3f}\nt_ket_thuc={t_ket_thuc:.3f}\nso_luot={so_luot}\n", encoding="utf-8")

    def tom_tat(nhan: str, rows: list[dict]) -> None:
        tv = [r["trung_vi_ms"] for r in rows]
        print(f"  {nhan:10s} n={len(rows):2d}  trung vị {statistics.median(tv):7.1f} ms  "
              f"p90 {phan_vi(tv, 0.9):7.1f} ms  max {max(tv):7.1f} ms")

    print()
    tom_tat("tất cả", hang)
    for nhom in NHOM.values():
        tom_tat(nhom, [r for r in hang if r["nhom"] == nhom])
    print(f"  Ảnh có chạy bước kiểu dáng: {sum(1 for r in hang if r['kieu_dang'])}/{len(hang)}")
    print(f"  Vòng đo: {t_ket_thuc - t_bat_dau:.1f} giây cho {so_luot} lượt")
    print(f"\nĐã ghi {args.out}")


if __name__ == "__main__":
    main()
