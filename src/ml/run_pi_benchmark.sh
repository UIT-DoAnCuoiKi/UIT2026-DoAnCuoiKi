#!/usr/bin/env bash
# Chạy trọn bộ benchmark trên Raspberry Pi 5, vừa đo thời gian vừa ghi log điện năng.
#
# Vì sao gộp vào một script thay vì gõ tay từng lệnh: số công suất chỉ có nghĩa khi
# biết nó đo lúc máy đang làm gì. Script ghi mốc bắt đầu, kết thúc và nhiệt độ lúc
# bắt đầu của từng loạt vào moc_thoi_gian.csv, sau đó summarize_pi_benchmark.py
# ghép log điện theo mốc đó.
#
# Bố cục một lần chạy:
#   1. Nghỉ 60 giây lấy đường nền, để tách phần điện do suy luận khỏi phần điện Pi
#      luôn tiêu dù không làm gì.
#   2. Chín loạt: ba mức luồng (1, 2, 4 vì Pi 5 có 4 lõi) nhân ba cấu hình model
#      (xem CAU_HINH bên dưới).
#   3. Ba loạt tải liên tục 60 lượt ở 4 luồng, mỗi cấu hình một loạt. Loạt ngắn có
#      xen thời gian nạp model nên công suất bị pha loãng, loạt dài mới cho công suất
#      lúc suy luận liên tục.
#   4. Nghỉ 60 giây lấy đường nền lần hai.
#
# Trước mỗi bước, script chờ SoC nguội về dưới NGUONG_NGUOI_C. Lần chạy đầu không
# chờ thì nhiệt dồn qua các loạt: loạt cuối chạm giới hạn nhiệt mềm 80°C
# (throttled=0x80008), đường nền cuối buổi cao hơn đầu buổi 20%, và cấu hình chạy sau
# luôn nóng hơn cấu hình chạy trước nên so sánh không công bằng. Số liệu lần đó giữ ở
# experiments/pi5_lan1_khong_cho_nguoi/ để đối chiếu.
#
# Ngưỡng 58°C chứ không thấp hơn: quạt mặc định của Pi 5 quay chậm dần khi SoC dưới
# 60°C, nên lúc nghỉ SoC đứng quanh 55-56°C (đo được: 55,6°C suốt hơn 1 phút, quạt
# 3850 vòng/phút). Đặt 50°C thì không bao giờ tới, loạt nào cũng chờ hết giới hạn.
# Mục đích là mọi loạt bắt đầu cùng một trạng thái nhiệt, không phải thật mát.
#
# Chạy trên Pi:  bash src/ml/run_pi_benchmark.sh
# Ghi ra thư mục khác:  OUT=src/ml/experiments/ten_khac bash src/ml/run_pi_benchmark.sh
set -euo pipefail

REPO="${REPO:-$HOME/smartpark}"
PY="${PY:-$HOME/sp-venv/bin/python}"
OUT="${OUT:-$REPO/src/ml/experiments/pi5}"
NGUONG_NGUOI_C=58
mkdir -p "$OUT"

DIEN="$OUT/nhat_ky_dien.csv"
MOC="$OUT/moc_thoi_gian.csv"
cd "$REPO"

# <tên cấu hình>|<model định vị xe>|<model kiểu dáng>. Đặt tường minh cả hai biến cho
# mọi cấu hình; benchmark_pipeline.py in lại tên model thật sự chạy ở đầu mỗi log.
# Lần đo trước, script benchmark không đọc ML_COARSE_WEIGHTS nên loạt gắn nhãn "onnx"
# vẫn chạy .pt mà không log nào cho thấy.
CAU_HINH=(
  "pt|yolov8n.pt|vehicle-style-resnet18.onnx"
  "onnx|yolov8n.onnx|vehicle-style-resnet18.onnx"
  "onnx_mnv3|yolov8n.onnx|vehicle-style-mobilenet_v3_small.onnx"
)

nhiet_do() { echo $(( $(cat /sys/class/thermal/thermal_zone0/temp) / 1000 )); }

# Ghi cấu hình máy vào file để báo cáo trích từ đây, không gõ tay.
{
  echo "thoi_diem: $(date -Is)"
  echo "model: $(tr -d '\0' < /proc/device-tree/model)"
  echo "revision: $(awk '/^Revision/ {print $3}' /proc/cpuinfo)"
  echo "ram_mb: $(free -m | awk '/^Mem:/ {print $2}')"
  echo "he_dieu_hanh: $(. /etc/os-release && echo "$PRETTY_NAME")"
  echo "kernel: $(uname -r)"
  echo "firmware: $(vcgencmd version | head -1)"
  # Dòng tối đa nguồn khai báo khi thương lượng USB-C PD (mA). Củ chính hãng 27W là 5000.
  echo "nguon_max_ma: $(od -An -tu4 --endian=big /proc/device-tree/chosen/power/max_current 2>/dev/null | tr -d ' ' || echo khong_doc_duoc)"
  echo "quat_rpm_luc_bat_dau: $(cat /sys/devices/platform/cooling_fan/hwmon/*/fan1_input 2>/dev/null || echo khong_co_quat)"
  echo "o_dia_goc: $(findmnt -no SOURCE /)"
  echo "governor_cpu: $(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor)"
  echo "python: $("$PY" -c 'import platform; print(platform.python_version())')"
  echo "nguong_cho_nguoi_c: $NGUONG_NGUOI_C"
} > "$OUT/may_do.txt"

echo "nhan,t_bat_dau,t_ket_thuc,nhiet_do_bat_dau_c,giay_cho_nguoi" > "$MOC"

"$PY" src/ml/pi_power_monitor.py --out "$DIEN" --interval 1.0 &
PID_DIEN=$!
trap 'kill "$PID_DIEN" 2>/dev/null || true' EXIT
sleep 3   # để bộ đo ghi được vài mẫu trước mốc đầu tiên

# Chờ nguội, tối đa 5 phút. In ra số giây đã chờ.
cho_nguoi() {
  local bat_dau=$SECONDS han=$((SECONDS + 300))
  while [ "$(nhiet_do)" -gt "$NGUONG_NGUOI_C" ]; do
    [ "$SECONDS" -ge "$han" ] && { echo "### hết 5 phút vẫn $(nhiet_do)°C, đo tiếp" >&2; break; }
    sleep 5
  done
  echo $((SECONDS - bat_dau))
}

moc() {  # moc <nhãn> <lệnh...>
  local nhan="$1"; shift
  local cho nd t0 t1
  cho=$(cho_nguoi)
  nd=$(nhiet_do)
  t0=$(date +%s.%N)
  echo "### [$nhan] bắt đầu $(date -Is) ở ${nd}°C (đã chờ nguội ${cho}s)" >&2
  "$@"
  t1=$(date +%s.%N)
  echo "$nhan,$t0,$t1,$nd,$cho" >> "$MOC"
  echo "### [$nhan] xong sau $(echo "$t1 - $t0" | bc) giây" >&2
}

chay() {  # chay <nhãn> <số luồng> <model định vị> <model kiểu dáng> [tham số thêm]
  local nhan="$1" luong="$2" coarse="$3" style="$4"; shift 4
  moc "$nhan" env ML_INTRAOP_THREADS="$luong" \
    ML_COARSE_WEIGHTS="src/ml/weights/$coarse" ML_STYLE_ONNX="src/ml/weights/$style" \
    "$PY" src/ml/benchmark_pipeline.py "$@" \
    > "$OUT/$nhan.log" 2>&1
}

moc nghi_truoc sleep 60

for ch in "${CAU_HINH[@]}"; do
  IFS="|" read -r ten coarse style <<< "$ch"
  for n in 1 2 4; do
    chay "bench_${ten}_${n}luong" "$n" "$coarse" "$style"
  done
done

for ch in "${CAU_HINH[@]}"; do
  IFS="|" read -r ten coarse style <<< "$ch"
  chay "tai_lien_tuc_${ten}_4luong" 4 "$coarse" "$style" --runs 60 --warmup 5
done

moc nghi_sau sleep 60

kill "$PID_DIEN" 2>/dev/null || true
wait "$PID_DIEN" 2>/dev/null || true
echo
echo "Xong. Kết quả trong $OUT:"
ls -la "$OUT"
