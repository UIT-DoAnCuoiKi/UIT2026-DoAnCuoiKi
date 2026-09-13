"""Ghi log công suất, nhiệt độ và tải CPU của Raspberry Pi 5 trong lúc chạy benchmark.

CÁCH ĐO (viết ở đây để tái lập và để trả lời khi bảo vệ):

1. Nguồn số công suất: Pi 5 dùng chip quản lý nguồn Renesas DA9091 (PMIC), bên
   trong có sẵn ADC đo dòng và áp của từng nhánh nguồn trên bo. Firmware cho đọc
   qua `vcgencmd pmic_read_adc`. Đây là số đo bằng phần cứng, không phải mô hình
   ước lượng theo tần số hay theo phần trăm CPU. Pi 4 không có, chỉ Pi 5 làm được.

2. Công thức: mỗi nhánh có một cặp `<TÊN>_A` (dòng, ampe) và `<TÊN>_V` (áp, vôn).
       P_nhánh = V_nhánh × I_nhánh
       P_tổng  = Σ P_nhánh
   Chỉ cộng nhánh có đủ cả cặp. `EXT5V_V` và `BATT_V` bị loại vì chỉ có áp, không
   có dòng tương ứng.

3. Phạm vi: đây là công suất các nhánh nguồn do PMIC cấp trên bo, không phải công
   suất đo ở ổ điện. Không tính hao hụt của củ sạc, hao hụt khâu hạ áp 5V xuống
   các nhánh, quạt tản nhiệt và thiết bị cắm cổng USB, vì chúng lấy điện thẳng từ
   đường 5V chứ không qua PMIC. Số này là cận dưới của điện năng thật; muốn số ở
   ổ điện phải có đồng hồ đo USB-C rời.

4. Nhiệt độ và giảm xung là điều kiện hợp lệ của phép đo. Pi 5 tự hạ xung khi
   nóng. Cột `throttled` ghi nguyên giá trị `vcgencmd get_throttled`, gồm hai phần:
   bit 0-3 là trạng thái tại lúc lấy mẫu (0 sụt áp, 1 giới hạn xung, 2 đang hạ
   xung, 3 chạm giới hạn nhiệt mềm), bit 16-19 là cờ dính "đã từng xảy ra" cùng
   thứ tự, chỉ xoá khi reboot. Xét một loạt thì chỉ nhìn bit 0-3. Tốc độ quạt ghi
   kèm để giải thích diễn biến nhiệt độ, quạt không nằm trong số công suất (mục 3).

5. Chi phí của chính bộ đo: mỗi mẫu gọi `vcgencmd` 2 lần (đọc PMIC và đọc cờ giảm
   xung), vài mili giây, mặc định 1 giây một lần. Phần này nằm trong số công suất
   đo được, nhưng giống nhau lúc nghỉ và lúc tải nên không ảnh hưởng hiệu số.

Chạy trên Pi:
    python3 src/ml/pi_power_monitor.py --out nhat_ky_dien.csv
    # Ctrl+C hoặc SIGTERM để dừng. File ghi xả sau mỗi dòng nên không mất dữ liệu.
"""

from __future__ import annotations

import argparse
import csv
import glob
import re
import signal
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

SYSFS_TEMP = Path("/sys/class/thermal/thermal_zone0/temp")
SYSFS_FREQ = Path("/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq")
SYSFS_FAN_GLOB = "/sys/devices/platform/cooling_fan/hwmon/*/fan1_input"
PROC_STAT = Path("/proc/stat")

# 3V7_WL_SW_A current(0)=0.05855580A  /  3V7_WL_SW_V volt(8)=3.70441600V
RE_ADC = re.compile(r"^\s*(\S+?)_(A|V)\s+(?:current|volt)\(\d+\)=([\d.]+)[AV]\s*$")

_dang_chay = True


def _dung(signum, frame):  # noqa: ARG001
    global _dang_chay
    _dang_chay = False


def doc_pmic() -> tuple[float, dict[str, float]]:
    """Trả về (tổng watt, công suất từng nhánh). Chỉ cộng nhánh có đủ cặp dòng + áp."""
    out = subprocess.run(
        ["vcgencmd", "pmic_read_adc"], capture_output=True, text=True, check=True
    ).stdout
    dong: dict[str, float] = {}
    ap: dict[str, float] = {}
    for dong_txt in out.splitlines():
        m = RE_ADC.match(dong_txt)
        if not m:
            continue
        ten, loai, gia_tri = m.group(1), m.group(2), float(m.group(3))
        (dong if loai == "A" else ap)[ten] = gia_tri

    cong_suat = {ten: ap[ten] * i for ten, i in dong.items() if ten in ap}
    return sum(cong_suat.values()), cong_suat


def doc_throttled() -> str:
    out = subprocess.run(
        ["vcgencmd", "get_throttled"], capture_output=True, text=True, check=True
    ).stdout
    return out.strip().split("=", 1)[-1]


def doc_nhiet_do() -> float:
    return int(SYSFS_TEMP.read_text()) / 1000.0


def doc_xung_mhz() -> float:
    try:
        return int(SYSFS_FREQ.read_text()) / 1000.0
    except OSError:
        return float("nan")


def doc_quat_rpm() -> float:
    duong_dan = glob.glob(SYSFS_FAN_GLOB)
    if not duong_dan:
        return float("nan")
    try:
        return float(Path(duong_dan[0]).read_text())
    except (OSError, ValueError):
        return float("nan")


def doc_jiffies() -> tuple[int, int]:
    """(tổng jiffies, jiffies nhàn rỗi) của dòng `cpu` gộp trong /proc/stat."""
    truong = [int(x) for x in PROC_STAT.read_text().split("\n", 1)[0].split()[1:]]
    nhan_roi = truong[3] + truong[4]  # idle + iowait
    return sum(truong), nhan_roi


def main() -> None:
    ap_cli = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap_cli.add_argument("--out", required=True, help="file CSV để ghi")
    ap_cli.add_argument("--interval", type=float, default=1.0, help="giây giữa hai mẫu (mặc định 1)")
    ap_cli.add_argument("--nhan", default="", help="nhãn ghi kèm mọi dòng, để lọc lại sau")
    args = ap_cli.parse_args()

    signal.signal(signal.SIGINT, _dung)
    signal.signal(signal.SIGTERM, _dung)

    _, nhanh_mau = doc_pmic()
    ten_nhanh = sorted(nhanh_mau)
    cot = ["thoi_diem", "t_unix", "nhan", "p_tong_w", "nhiet_do_c", "xung_mhz", "quat_rpm", "cpu_pct", "throttled"]
    cot += [f"p_{t.lower()}_w" for t in ten_nhanh]

    f = open(args.out, "w", newline="", encoding="utf-8")
    w = csv.writer(f)
    w.writerow(cot)

    tong_truoc, roi_truoc = doc_jiffies()
    print(f"Ghi {args.out}, {args.interval}s/mẫu, {len(ten_nhanh)} nhánh nguồn. Ctrl+C để dừng.", flush=True)

    while _dang_chay:
        time.sleep(args.interval)
        tong, roi = doc_jiffies()
        d_tong, d_roi = tong - tong_truoc, roi - roi_truoc
        cpu_pct = 100.0 * (1 - d_roi / d_tong) if d_tong else 0.0
        tong_truoc, roi_truoc = tong, roi

        p_tong, nhanh = doc_pmic()
        now = time.time()
        w.writerow(
            [
                datetime.fromtimestamp(now).isoformat(timespec="milliseconds"),
                f"{now:.3f}",
                args.nhan,
                f"{p_tong:.4f}",
                f"{doc_nhiet_do():.1f}",
                f"{doc_xung_mhz():.0f}",
                f"{doc_quat_rpm():.0f}",
                f"{cpu_pct:.1f}",
                doc_throttled(),
            ]
            + [f"{nhanh.get(t, 0.0):.5f}" for t in ten_nhanh]
        )
        f.flush()

    f.close()
    print(f"\nĐã dừng, ghi xong {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
