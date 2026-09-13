#!/usr/bin/env bash
# Đo pipeline trên 50 ảnh camera cổng thật trên Raspberry Pi 5, ghi log điện năng song song.
#
# Khác run_pi_benchmark.sh: đo trên nhiều ảnh thật (benchmark_anh_that.py) thay vì 1 ảnh
# mẫu, và trong mỗi mốc thời gian chỉ có vòng gọi run(), nên công suất trong mốc là của
# riêng suy luận chứ không trộn với phần đo từng model hay từng bước.
#
# Bố cục: nghỉ 60 giây -> từng cấu hình (4 luồng) -> nghỉ 60 giây.
# Chạy trên Pi:  bash src/ml/run_pi_anh_that.sh
set -euo pipefail

REPO="${REPO:-$HOME/smartpark}"
PY="${PY:-$HOME/sp-venv/bin/python}"
OUT="${OUT:-$REPO/src/ml/experiments/pi5_anh_that}"
SO_VONG="${SO_VONG:-5}"
mkdir -p "$OUT"
cd "$REPO"

# <tên>|<model định vị xe>|<model kiểu dáng>
CAU_HINH=(
  "pt_mnv3|yolov8n.pt|vehicle-style-mobilenet_v3_small.onnx"
  "pt_resnet|yolov8n.pt|vehicle-style-resnet18.onnx"
)

echo "nhan,t_bat_dau,t_ket_thuc" > "$OUT/moc_thoi_gian.csv"
"$PY" src/ml/pi_power_monitor.py --out "$OUT/nhat_ky_dien.csv" --interval 1.0 &
PID_DIEN=$!
trap 'kill "$PID_DIEN" 2>/dev/null || true' EXIT
sleep 3

nghi() {  # nghi <nhãn>
  local t0 t1
  t0=$(date +%s.%N); sleep 60; t1=$(date +%s.%N)
  echo "$1,$t0,$t1" >> "$OUT/moc_thoi_gian.csv"
}

nghi nghi_truoc
for ch in "${CAU_HINH[@]}"; do
  IFS="|" read -r ten coarse style <<< "$ch"
  echo "### $ten bắt đầu $(date -Is)" >&2
  env ML_INTRAOP_THREADS=4 \
    ML_COARSE_WEIGHTS="src/ml/weights/$coarse" ML_STYLE_ONNX="src/ml/weights/$style" \
    "$PY" src/ml/benchmark_anh_that.py --so-vong "$SO_VONG" --out "$OUT/$ten.csv" \
    > "$OUT/$ten.log" 2>&1
  # Mốc lấy từ chính script đo, bao đúng vòng gọi run(), không gồm lúc nạp model
  . <(sed 's/^/local_/' "$OUT/${ten}_moc.txt")
  echo "$ten,$local_t_bat_dau,$local_t_ket_thuc" >> "$OUT/moc_thoi_gian.csv"
done
nghi nghi_sau

kill "$PID_DIEN" 2>/dev/null || true
wait "$PID_DIEN" 2>/dev/null || true
echo "Xong: $OUT"
ls -la "$OUT"
