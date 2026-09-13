"""Đo độ trễ đầu-cuối qua API thật: POST /captures/infer, tính từ phía client.

Khác benchmark_anh_that.py (chỉ đo run()): số ở đây gồm cả truyền HTTP, đọc và giải mã
ảnh, suy luận, ghi cơ sở dữ liệu, lưu ảnh và phát sự kiện WebSocket, tức gần với thời
gian nhân viên chờ sau khi bấm chụp. Chạy cùng máy với backend (localhost) nên chưa gồm
độ trễ mạng LAN.

Phần ngoài suy luận tính trên cùng một request: khi bật dev_mode, phản hồi có
`timings_ms.tong` là tổng thời gian các bước pipeline có bấm giờ, nên
    ngoài suy luận = thời gian phía client - timings_ms.tong
Phần này gồm HTTP, giải mã ảnh, ghi cơ sở dữ liệu và đoạn code không bấm giờ giữa các bước.
Không so với một lần chạy benchmark khác, vì hai lần chạy ở hai thời điểm khác nhau.

Lượt đầu tiên ghi riêng: backend nạp model lười ở lượt chụp đầu nên lượt này chậm hơn hẳn.

Nên chạy với một bản backend riêng trỏ vào bản sao cơ sở dữ liệu, vì mỗi lượt gọi đều ghi
dữ liệu. Tài khoản đọc từ biến môi trường ADMIN_USERNAME, ADMIN_PASSWORD.

Chạy:
    ADMIN_USERNAME=... ADMIN_PASSWORD=... python src/ml/do_tre_api.py --url http://localhost:8001 --out ket_qua.csv
"""
from __future__ import annotations

import argparse
import csv
import os
import statistics
import sys
import time
import uuid
from pathlib import Path

import requests

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

REPO_ROOT = Path(__file__).resolve().parents[2]
THU_MUC_ANH = REPO_ROOT / "data" / "raw" / "kaggle_vn_plate_segment" / "images" / "val"
DANH_SACH = REPO_ROOT / "src" / "ml" / "data" / "anh_cong_benchmark.txt"


def dang_nhap(url: str) -> str:
    body = {"username": os.environ["ADMIN_USERNAME"], "password": os.environ["ADMIN_PASSWORD"]}
    r = requests.post(url + "/auth/login", json=body, timeout=30)
    if r.status_code != 200:
        raise RuntimeError(f"đăng nhập thất bại: {r.status_code} {r.text[:200]}")
    return r.json()["access_token"]


def phan_vi(x: list[float], q: float) -> float:
    s = sorted(x)
    k = (len(s) - 1) * q
    lo, hi = int(k), min(int(k) + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url", default="http://localhost:8001")
    ap.add_argument("--so-vong", type=int, default=3)
    ap.add_argument("--out", type=Path, default=Path("do_tre_api.csv"))
    args = ap.parse_args()

    headers = {"Authorization": f"Bearer {dang_nhap(args.url)}"}
    ten_anh = [d.strip() for d in DANH_SACH.read_text(encoding="utf-8").splitlines() if d.strip()]
    du_lieu = [(t, (THU_MUC_ANH / t).read_bytes()) for t in ten_anh]

    def goi(ten: str, raw: bytes) -> dict:
        t0 = time.perf_counter()
        r = requests.post(
            args.url + "/captures/infer",
            data={"capture_id": f"do-tre-{uuid.uuid4().hex[:12]}", "direction": "in"},
            files={"image": (ten, raw, "image/png")},
            headers=headers, timeout=120,
        )
        ms = (time.perf_counter() - t0) * 1000
        body = r.json() if r.status_code == 200 else {}
        tong = (body.get("timings_ms") or {}).get("tong")
        return {"anh": ten, "ms": round(ms, 1), "http": r.status_code,
                "suy_luan_backend_ms": None if tong is None else round(tong, 1),
                "ngoai_suy_luan_ms": None if tong is None else round(ms - tong, 1),
                "loai_xe": body.get("vehicle_type") or "", "bien": body.get("plate_text") or ""}

    dau = goi(*du_lieu[0])
    hang = []
    for vong in range(args.so_vong):
        for ten, raw in du_lieu:
            hang.append({"vong": vong + 1, **goi(ten, raw)})

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(hang[0]))
        w.writeheader()
        w.writerows(hang)
    args.out.with_name(args.out.stem + "_luot_dau.txt").write_text(
        f"luot_dau_ms={dau['ms']}\nhttp={dau['http']}\nsuy_luan_backend_ms={dau['suy_luan_backend_ms']}\n", encoding="utf-8")

    ok = [h for h in hang if h["http"] == 200]

    def trung_vi_theo_anh(truong: str) -> list[float]:
        g: dict[str, list[float]] = {}
        for h in ok:
            if h[truong] is not None:
                g.setdefault(h["anh"], []).append(h[truong])
        return [statistics.median(v) for v in g.values()]

    print(f"Lượt đầu tiên (backend nạp model): {dau['ms']:.0f} ms, HTTP {dau['http']}")
    print(f"{len(hang)} lượt, {len(hang) - len(ok)} lượt lỗi HTTP, "
          f"{sum(1 for h in ok if h['loai_xe'])} lượt có loại xe, {sum(1 for h in ok if h['bien'])} lượt có biển")
    for nhan, truong in [("Đầu-cuối phía client", "ms"), ("Các bước suy luận (tong)", "suy_luan_backend_ms"),
                         ("Ngoài suy luận", "ngoai_suy_luan_ms")]:
        tv = trung_vi_theo_anh(truong)
        if tv:
            print(f"{nhan:26s} trên {len(tv)} ảnh: trung vị {statistics.median(tv):6.1f} ms, "
                  f"p90 {phan_vi(tv, 0.9):6.1f} ms, max {max(tv):6.1f} ms")
    print(f"Đã ghi {args.out}")


if __name__ == "__main__":
    main()
