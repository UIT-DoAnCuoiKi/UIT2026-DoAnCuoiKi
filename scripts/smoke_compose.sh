#!/bin/sh
set -e
BASE=${BASE:-http://localhost:8000}
ADMIN_USER=${ADMIN_USERNAME:-admin}
ADMIN_PASS=${ADMIN_PASSWORD:-admin12345}

echo "1. health"
curl -sf "$BASE/health"; echo

echo "2. login admin"
TOKEN=$(curl -sf -X POST "$BASE/auth/login" -H 'Content-Type: application/json' \
  -d "{\"username\":\"$ADMIN_USER\",\"password\":\"$ADMIN_PASS\"}" | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")
echo "token len: ${#TOKEN}"

echo "3. tạo bảng giá o_to_con"
curl -sf -X POST "$BASE/price-rules" -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"vehicle_group":"o_to_con","mode":"block","unit_price":5000,"block_minutes":60}'; echo

echo "4. capture mới nhất (từ edge worker giả lập)"
curl -sf "$BASE/captures/latest"; echo

echo "smoke xong"
