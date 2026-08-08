"""Lấy mẫu mức dùng CPU/RAM/GPU theo chu kỳ trong lúc huấn luyện.

Chạy song song với src/ml/train_vehicle_classifier.py (tiến trình riêng, không
nằm trong pipeline huấn luyện) để có số liệu tài nguyên thật cho báo cáo.

Chạy: .venv/Scripts/python.exe src/ml/monitor_resources.py --out train_resource_usage.csv
"""

from __future__ import annotations

import argparse
import csv
import datetime
import subprocess
import time

import psutil


def read_gpu() -> tuple[float | None, float | None, float | None]:
    """Đọc (gpu_util_pct, gpu_mem_used_mb, gpu_mem_total_mb) qua nvidia-smi.

    Trả về (None, None, None) nếu máy không có GPU NVIDIA hoặc nvidia-smi lỗi,
    để việc lấy mẫu CPU/RAM vẫn chạy bình thường.
    """
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=utilization.gpu,memory.used,memory.total",
             "--format=csv,noheader,nounits"],
            text=True, timeout=5,
        )
        util, used, total = (float(x) for x in out.strip().split(","))
        return util, used, total
    except Exception:
        return None, None, None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="train_resource_usage.csv")
    parser.add_argument("--interval", type=float, default=5.0, help="số giây giữa 2 lần lấy mẫu")
    args = parser.parse_args()

    fields = ["timestamp", "cpu_pct", "ram_used_gb", "ram_total_gb", "gpu_util_pct", "gpu_mem_used_mb", "gpu_mem_total_mb"]
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(fields)
        f.flush()
        print(f"Ghi mức dùng tài nguyên mỗi {args.interval}s vào {args.out}, Ctrl+C để dừng")
        try:
            while True:
                cpu_pct = psutil.cpu_percent(interval=None)
                vm = psutil.virtual_memory()
                gpu_util, gpu_used, gpu_total = read_gpu()
                row = [
                    datetime.datetime.now().isoformat(timespec="seconds"),
                    cpu_pct,
                    round(vm.used / 1e9, 2),
                    round(vm.total / 1e9, 2),
                    gpu_util,
                    gpu_used,
                    gpu_total,
                ]
                writer.writerow(row)
                f.flush()
                print(row)
                time.sleep(args.interval)
        except KeyboardInterrupt:
            print("Đã dừng lấy mẫu.")


if __name__ == "__main__":
    main()
