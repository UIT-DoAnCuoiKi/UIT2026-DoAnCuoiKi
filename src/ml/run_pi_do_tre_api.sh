#!/usr/bin/env bash
# Đo độ trễ đầu-cuối qua API trên Raspberry Pi 5 (do_tre_api.py).
#
# Chạy một bản backend riêng ở cổng 8001, cùng cấu hình model với service
# smartpark-backend, nhưng trỏ vào bản sao cơ sở dữ liệu và thư mục ảnh tạm, vì mỗi
# lượt gọi /captures/infer đều ghi dữ liệu. Backend chính được dừng trong lúc đo để
# không tranh CPU, đo xong bật lại.
#
# Chạy trên Pi:  bash src/ml/run_pi_do_tre_api.sh
set -euo pipefail

REPO="${REPO:-$HOME/smartpark}"
PY="${PY:-$HOME/sp-venv/bin/python}"
OUT="${OUT:-$REPO/src/ml/experiments/pi5_do_tre_api}"
CONG=8001
TAM=$(mktemp -d)
mkdir -p "$OUT"

systemctl --user stop smartpark-backend
cleanup() {
  [ -n "${PID_BE:-}" ] && kill "$PID_BE" 2>/dev/null || true
  rm -rf "$TAM"
  systemctl --user start smartpark-backend
}
trap cleanup EXIT

cp "$REPO/src/backend/dev.db" "$TAM/do_tre.db"
mkdir -p "$TAM/images"

cd "$REPO/src/backend"
# Cùng biến model với ~/.config/systemd/user/smartpark-backend.service
env INFERENCE_ENGINE=ml ML_INTRAOP_THREADS=4 \
  ML_PLATE_WEIGHTS="$REPO/src/ml/plate_detection_pipeline/weights/yolov8n_a1_640.onnx" \
  ML_COARSE_WEIGHTS="$REPO/src/ml/weights/yolov8n.pt" \
  DATABASE_URL="sqlite:///$TAM/do_tre.db" IMAGE_STORAGE_DIR="$TAM/images" \
  "$PY" -m uvicorn app.main:app --host 127.0.0.1 --port "$CONG" > "$OUT/backend.log" 2>&1 &
PID_BE=$!

for _ in $(seq 1 60); do
  curl -sf "http://127.0.0.1:$CONG/health" > /dev/null && break
  sleep 1
done

# Tài khoản admin lấy từ .env của backend, không in ra
ADMIN_USERNAME=$(grep -E '^ADMIN_USERNAME=' .env | cut -d= -f2-)
ADMIN_PASSWORD=$(grep -E '^ADMIN_PASSWORD=' .env | cut -d= -f2-)
export ADMIN_USERNAME ADMIN_PASSWORD

cd "$REPO"
"$PY" src/ml/do_tre_api.py --url "http://127.0.0.1:$CONG" --so-vong 3 --out "$OUT/do_tre_api.csv" | tee "$OUT/do_tre_api.log"
