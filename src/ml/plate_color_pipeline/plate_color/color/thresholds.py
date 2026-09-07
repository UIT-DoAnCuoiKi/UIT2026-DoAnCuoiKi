"""Tunable HSV thresholds for Vietnamese licence-plate colour classification.

All constants live here as a single tuning surface — adjust these to recalibrate
without touching classifier logic.

OpenCV HSV encoding used throughout:
  H: 0–179  (OpenCV halves the usual 0–360° so it fits in uint8)
  S: 0–255
  V: 0–255
"""
from __future__ import annotations

# ── achromatic (white/grey) gate ──────────────────────────────────────────────
# White pixels are low-saturation AND bright.  S < 55 keeps grey borders out;
# V ≥ 110 rejects dark neutral areas (tyre rubber, shadow patches).
WHITE_SAT_MAX = 55          # S strictly below → candidate is achromatic
WHITE_VAL_MIN = 110         # V at/above → bright enough to call white

# ── saturation gate for chromatic hue bands ───────────────────────────────────
# Pixels below this threshold are washed-out or grey and should not vote for
# any hue bucket; 55 is empirically the smallest value that still rejects
# off-white plate borders under CLAHE enhancement.
SAT_MIN_FOR_HUE = 55        # S at/above → saturated, eligible for hue test

# ── hue bands (H in 0–179) ───────────────────────────────────────────────────
# Red wraps around the HSV cylinder: in OpenCV space it occupies two arcs,
# 0–11 (orange-red through pure red) and 160–179 (magenta-red through red).
# We split the test into < HUE_RED_HI OR >= HUE_RED_WRAP to capture both arcs.
HUE_RED_HI   = 12           # H < 12 → red arc near 0°
HUE_RED_WRAP = 160          # H ≥ 160 → red arc near 360° (wraps to 0)

# Yellow: H 12–34 in OpenCV (≈ 24–68° in standard HSV).
# Vietnamese plate yellow is a warm amber-yellow centred around H ≈ 25.
HUE_YELLOW_LO = 12
HUE_YELLOW_HI = 35          # exclusive upper bound (H < 35)

# Blue: H 85–139 in OpenCV (≈ 170–278° in standard HSV).
# Covers sky-blue through cobalt; VN blue plates sit around H ≈ 105–115.
HUE_BLUE_LO = 85
HUE_BLUE_HI  = 140          # exclusive upper bound (H < 140)

# ── confidence / coverage gates ───────────────────────────────────────────────
# If too few pixels fall into any classifiable category the result is noise;
# 0.15 means at least 15 % of the crop must be white/red/yellow/blue.
MIN_CONSIDERED_FRAC = 0.15  # classifiable fraction below this → unknown

# The winning colour must dominate by at least this share of classifiable pixels.
# 0.35 prevents a split vote (e.g. half white text + half yellow bg) from picking
# either colour with false confidence.
CONF_FLOOR = 0.35           # winner share below this → unknown

# ── xác định vùng nền biển thật trước khi tính màu ────────────────────────────
# pad=4 mặc định của PlateDetector (plate_detection_pipeline) cộng thêm biên
# quanh bbox YOLO; viền này (+ quang sai màu/nén JPEG ở rìa crop nhỏ) có thể
# lệch hue khỏi nền biển thật, gây nhận nhầm màu (đo thực nghiệm: biển trắng
# CarLongPlate306 bị đọc thành "blue" do đúng dải viền này). Dùng Otsu +
# contour lớn nhất (cùng kỹ thuật deskew() trong pipeline/ocr.py) để tìm đúng
# vùng nền biển, bỏ viền nhiễu, thay vì đoán 1 tỉ lệ % cố định.
COLOR_MIN_CONTOUR_AREA_FRAC = 0.3  # contour lớn nhất phải chiếm tối thiểu 30% crop mới tin cậy (giống ngưỡng deskew())

# ── 2 lỗi thật đã ghi nhận, CHƯA SỬA (test trên ảnh thật, không phải suy đoán) ─
#
# (a) Biển trắng bị đọc thành "blue" khi cả khung hình bị ám màu xanh (đèn LED/
#     ánh sáng đêm) — khác lỗi viền crop ở trên, lần này cả nền biển thật sự lệch
#     hue chứ không phải do rìa crop. Đo trên 1 ảnh camera cổng ban đêm thật:
#     nền biển trắng ra Hue≈95 (rơi đúng dải HUE_BLUE), kênh Blue trung bình cao
#     hơn hẳn kênh Red (183 so với 135). Cân bằng trắng kiểu gray-world SỬA ĐÚNG
#     case này (blue→white), nhưng lại làm giảm mạnh độ tin cậy của biển VÀNG
#     thật (đo trên ảnh khác: 77.6%→54.9%, kèm nhiễu màu ở viền chữ) — nên KHÔNG
#     thể bật gray-world WB vô điều kiện cho mọi ảnh, phải phát hiện được ảnh
#     nào thực sự bị ám màu trước (chưa có cơ chế này, xem thảo luận trong
#     phiên làm việc portal Trạm cổng ngày 2026-09-06 nếu cần chi tiết).
#
# (b) Biển XANH THẬT (chữ trắng, biển cơ quan nhà nước "80B...") bị đọc thành
#     "white" ngay cả ban ngày bình thường, KHÔNG liên quan ám màu. Nguyên nhân
#     khác hẳn: biển xanh navy tối/cũ có màu BGR gần cân bằng (đo được B≈72,
#     G≈64, R≈71 — kênh Blue và Red chỉ chênh 1 đơn vị). Với công thức
#     S=(max-min)/max của HSV, màu càng tối thì S càng bị thổi phồng giả tạo dù
#     kênh màu chỉ lệch chút ít, VÀ Hue trở nên cực kỳ không ổn định quanh điểm
#     Blue≈Red (nhiễu ảnh rất nhỏ đẩy Hue nhảy hẳn từ ~0° sang ~120°). Đo thực
#     tế: gần nửa số pixel nền (đúng 1 màu navy đồng nhất với mắt thường) bị
#     phân mảnh hue ra 2 cụm — ~40% rơi vào dải đỏ/vàng (Hue 0–20), phần còn lại
#     mới đúng dải xanh (Hue 110–140) — làm phiếu bầu "blue" bị pha loãng, thua
#     phiếu "white" (từ chữ trắng + phản chiếu sáng). Đây là điểm yếu của chính
#     công thức HSV với màu tối/ít bão hòa tuyệt đối, không sửa được bằng cách
#     lọc ám màu ở mục (a) — cần đổi hẳn cách đo (vd. hiệu số kênh màu tuyệt
#     đối, hoặc chuyển sang không gian màu LAB ổn định hơn với vùng tối) mới
#     giải quyết được, ngoài phạm vi sửa nhanh.
