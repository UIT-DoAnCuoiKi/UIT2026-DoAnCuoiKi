#!/usr/bin/env bash
# Đo bộ nhớ tối đa của tiến trình benchmark cho từng cấu hình model trên Raspberry Pi 5.
#
# Chạy benchmark_pipeline.py (4 luồng, 3 lượt) bên trong một tiến trình Python, cuối cùng
# in resource.getrusage(RUSAGE_SELF).ru_maxrss: bộ nhớ thường trú lớn nhất tiến trình từng
# dùng, đơn vị KiB trên Linux. Script benchmark nạp pipeline hai lần trong cùng tiến trình
# nên số này là cận trên cho một pipeline.
#
# Cấu hình giống run_pi_benchmark.sh. Chạy sau khi đo thời gian xong, không chạy song song,
# để không làm lệch số thời gian và công suất.
#
# Chạy trên Pi:  bash src/ml/run_pi_ram.sh
set -euo pipefail

REPO="${REPO:-$HOME/smartpark}"
PY="${PY:-$HOME/sp-venv/bin/python}"
OUT="${OUT:-$REPO/src/ml/experiments/pi5}"
cd "$REPO"
mkdir -p "$OUT"

CAU_HINH=(
  "pt|yolov8n.pt|vehicle-style-resnet18.onnx"
  "onnx|yolov8n.onnx|vehicle-style-resnet18.onnx"
  "onnx_mnv3|yolov8n.onnx|vehicle-style-mobilenet_v3_small.onnx"
)

for ch in "${CAU_HINH[@]}"; do
  IFS="|" read -r ten coarse style <<< "$ch"
  env ML_INTRAOP_THREADS=4 \
    ML_COARSE_WEIGHTS="src/ml/weights/$coarse" ML_STYLE_ONNX="src/ml/weights/$style" \
    "$PY" - > "$OUT/ram_${ten}_4luong.log" 2>&1 <<'PY'
import resource, runpy, sys
sys.argv = ["benchmark_pipeline.py", "--runs", "3", "--warmup", "1"]
runpy.run_path("src/ml/benchmark_pipeline.py", run_name="__main__")
print("ru_maxrss_kb=" + str(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss))
PY
  echo "$ten: $(grep ru_maxrss "$OUT/ram_${ten}_4luong.log")"
done
