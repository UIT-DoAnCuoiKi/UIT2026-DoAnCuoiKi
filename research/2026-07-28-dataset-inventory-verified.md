# Dataset đã TẢI VỀ + KIỂM TRA THỰC TẾ (verified inventory)

**Ngày:** 2026-07-28
**Mode:** 3 (dataset) — **không đoán, không giả định**: mọi số liệu dưới đây lấy từ **tải thật + mở file thật** (đếm ảnh, đọc annotation, đo kích thước, xem ảnh mẫu, phân tích màu HSV, thống kê class).
**Bổ sung cho:** [[2026-07-26-datasets-vietnam]] (khảo sát). File này = bằng chứng thực nghiệm.

**Công cụ:** Kaggle API (creds OK) tải trực tiếp; `inspect_ds.py` (đếm/format/dims/class), `color_check.py` (phân bố màu HSV), `montage.py` (lưới ảnh mẫu). Roboflow web 403 → dùng **mirror Kaggle** để lấy nội dung thật. Ảnh mẫu: `research/assets/dataset-samples/`.

**Nguồn KHÔNG tải được (còn thiếu):** Roboflow trực tiếp cần `ROBOFLOW_API_KEY` (chưa có); GitHub Google Drive (winter2897/trungdinh22) chưa tải đợt này. `ngkhtrf` (1 GB YOLO) chưa tải — để dành dung lượng.

---

## Bảng tổng hợp đã kiểm tra thật

| Key | Nguồn | Module | Ảnh (thật) | Format (thật) | Class (thật) | Kích thước | Verdict |
|---|---|---|---|---|---|---|---|
| **plate_tanhphp** | [Kaggle tanhphp](https://www.kaggle.com/datasets/tanhphp/vietnamese-license-plates) | Detect biển | **2.255** | YOLO bbox | nc=1 `Bien-so` (2.998 box) | 144–2048px, đa dạng | ⭐ **Dùng — detect chính** |
| **plate_segment_duydieu** | [Kaggle duydieunguyen](https://www.kaggle.com/datasets/duydieunguyen/licenseplates) | Detect + phân loại layout | **4.578** | **YOLO-SEG (polygon 4 điểm)** | **nc=2: BSD(dài/1 hàng)=1.641, BSV(vuông/2 hàng)=3.559** | 380–600px | ⭐ **Dùng — phân luồng 1/2 hàng + biển nghiêng** |
| **plate_bomaich_yolov7** | [Kaggle bomaich](https://www.kaggle.com/datasets/bomaich/vnlicenseplate) | Detect biển | 498 | YOLO bbox, split sẵn | nc=1 plate (780 box) | 571–1920px, ảnh cảnh đầy đủ | ✅ Dùng bổ sung |
| **plate_ocr_topkek** | [Kaggle topkek69](https://www.kaggle.com/datasets/topkek69/vietnamese-license-plate-ocr) | **OCR chuỗi** | **12.190** (6.643 crop thật + 5.547 sinh) | crop + CSV `Name,Label,Type` (vd `30F 11292`) | biển 1+2 hàng, type1–7 | 28–235px | ⭐ **Dùng — OCR chính** |
| **motorbike_ocr_100** | [Kaggle dtkngan](https://www.kaggle.com/datasets/dtkngan/100-bien-so-xe-may-ocr) | OCR xe máy 2 hàng | 116 | ảnh + txt = **chuỗi biển** (`59N187515`) | biển **xe máy 2 hàng** | 472×303 | ✅ Test set biển 2 hàng |
| **char_nguyenquanglinh** | [Kaggle nguyenquanglinh0109](https://www.kaggle.com/datasets/nguyenquanglinh0109/character-dataset-for-vietnam-license-plate) | Nhận dạng ký tự | 1.839 | **folder=class** (28×28) | 0-9, A-Z (thiếu vài chữ) + `Noise` | 28×28 | ⚠️ Dùng có điều kiện (lệch class) |
| **vehicle_lmphmthanh** | [Kaggle lmphmthanh](https://www.kaggle.com/datasets/lmphmthanh/vietnam-vehicle-dataset) = mirror Roboflow `car-classification/vietnamese-vehicle v3` | Loại xe | **2.361** | YOLO bbox | nc=4 (12.163 box; 1=4.230, 0=3.960, 2=3.310, 3=663) | 640×640 | ⭐ **Dùng — loại xe. License CC BY 4.0 XÁC MINH** |
| **vehicle_cameraview** | [Kaggle haihovan](https://www.kaggle.com/datasets/haihovan/vietnam-vehicles-camera-view) | Loại xe (CCTV) | 156 | YOLO **pose** (kpt_shape[1,3]) | nc=4 car/motorcycle/truck/bus; lệch **bus=2.387**, moto=52 | 406×266, ngã tư Nov-2025 | ⚠️ Nhỏ + lệch class, góc ngã tư |
| ~~plate_unidpro~~ | [Kaggle unidpro](https://www.kaggle.com/datasets/unidpro/license-plate-detection-dataset) | — | 100 | folder=class | **USA/Norway/Bahrain/Ireland** | — | ❌ **LOẠI — không phải VN** |
| ~~vehicle_hanoi~~ | [Kaggle thanhlamdev](https://www.kaggle.com/datasets/thanhlamdev/vehicle-at-ha-noi) | — | **0** | 2 file CSV | khảo sát đi lại (25.591 dòng) | — | ❌ **LOẠI — không có ảnh, là dữ liệu bảng** |

**Bài học:** usability rating cao ≠ hợp mục tiêu — `unidpro` (0.94) không phải VN; `vehicle_hanoi` (1.0) là CSV khảo sát. **Phải mở file mới biết.**

---

## Phân tích MÀU biển (thật — HSV, hỗ trợ module màu Đức)

Chạy `color_check.py` trên **599 crop biển thật** (topkek/cropped) — mask pixel chữ tối, lấy nền sáng:

| Màu | Số crop | Tỉ lệ | Ý nghĩa biển VN |
|---|---|---|---|
| **Trắng** | 372 | **62.1%** | cá nhân |
| **Vàng** | 115 | **19.2%** | kinh doanh/dịch vụ (nhiều sau chuyển đổi 2020) |
| **Xanh dương** | 57 | 9.5% | cơ quan nhà nước |
| **Đỏ** | 37 | 6.2% | quân đội |
| **Xanh lá** | 3 | 0.5% | biển điện/EV mới — **quá hiếm để train** |
| khác/tối | 15 | 2.5% | mờ/thiếu sáng |

**Kết luận màu (bằng chứng, không đoán):**
1. **Đủ 4 màu chính** (trắng/vàng/xanh/đỏ) trong data thật → module màu có nghĩa.
2. **HSV tách được** — 4 cụm hue/saturation rõ → **HSV+CLAHE khả thi** (đúng kế hoạch Đức), chưa cần CNN.
3. **Lệch nặng về trắng (62%)** + xanh lá gần như vắng → nếu train CNN màu phải xử lý imbalance; với HSV thì chỉ cần tune ngưỡng, không lo imbalance.
4. Cross-check trên duydieu (crop rộng hơn) cho trắng 84% — sai lệch do crop lẫn nền cảnh; **crop sát biển (topkek) là số đáng tin hơn.**

---

## Vấn đề chất lượng phát hiện thật (không đoán)

- **char_nguyenquanglinh lệch class nghiêm trọng:** đếm thật — `M=4, Y=19, Z=32` vs `F=148, G=85, Noise=124`. Ký tự hiếm (M) gần như không train được → **phải augment mạnh hoặc bổ sung**. Có thêm lớp `Noise` (124) — hữu ích lọc nhiễu.
- **duydieu format = polygon 4 điểm** (không phải bbox chuẩn): mỗi dòng `class + 8 tọa độ` → là **segmentation/oriented box**, hợp biển nghiêng nhưng cần train YOLO-seg hoặc convert polygon→bbox trước khi dùng detector thường.
- **vehicle_cameraview lệch class + là pose dataset:** bus=2.387 áp đảo, motorcycle chỉ 52 (ngược thực tế VN) + có keypoint → **không hợp** làm data loại xe chính; chỉ tham khảo góc CCTV.
- **topkek trộn ảnh thật (6.643) + sinh tổng hợp (5.547):** phải **tách generated/ khi đánh giá** (synthetic không tính vào test thật) để tránh thổi phồng accuracy.
- **Không archive nào kèm file LICENSE** trừ `vehicle_lmphmthanh` (nhúng `CC BY 4.0` trong data.yaml). Các bộ khác: license theo trang Kaggle, archive im lặng → **an toàn: train nội bộ, không phát hành lại**.

---

## Ảnh mẫu đã xem (research/assets/dataset-samples/)

| File | Xác nhận trực quan |
|---|---|
| `1_bomaich_detect.png` | Cảnh đường/bãi VN: ô tô + xe máy, biển rõ |
| `2_motorbike_ocr.png` | Đuôi xe máy VN, **biển 2 hàng** trong bãi |
| `3_vehicle_roboflow.png` | Giao thông VN thật: bus/ô tô/xe máy/tải |
| `4_topkek_crops.png` | Biển VN crop: đọc được `60K-394.40`, `54-T5 4498`, `29A-974.35`; đủ màu trắng/đỏ/xanh/vàng, cả 1+2 hàng |
| `5_cameraview.png` | CCTV ngã tư VN (góc trên cao) |
| `6_chars.png` | Ký tự 28×28 tách sẵn |

---

## Khuyến nghị CẬP NHẬT (sau kiểm tra thật)

| Module | Chốt dùng | Lý do (bằng chứng) |
|---|---|---|
| **Detect biển** | `plate_tanhphp` (2.255) + `plate_bomaich` (498) làm bbox; `duydieu` (4.578) cho **routing 1/2 hàng** | đã xác minh số ảnh + format; duydieu tách BSD/BSV = giải quyết luồng xe máy 2 hàng |
| **OCR** | `plate_ocr_topkek` (crop thật + label chuỗi) train chính; `motorbike_ocr_100` làm **test biển 2 hàng** | có sẵn cặp ảnh-chuỗi thật; tách synthetic khi đo |
| **Ký tự (nếu đi hướng char-classifier)** | `char_nguyenquanglinh` + augment lớp hiếm | lệch class đã đo, xử lý được |
| **Màu biển** | **HSV+CLAHE** (không cần CNN) | 4 màu tách được trên HSV, đo thật |
| **Loại xe** | `vehicle_lmphmthanh` (**CC BY 4.0**, 2.361, cân class) | license sạch + phân bố class ổn |
| **Loại/nguồn cần bổ sung** | Roboflow (cần API key), winter2897/trungdinh Drive, `ngkhtrf` | chưa tải đợt này |

## Còn thiếu → hành động
1. **ROBOFLOW_API_KEY** để tải bộ Roboflow gốc (8.397 ảnh school-fuhih) — nếu cần, cung cấp key.
2. **Biển 2 hàng ban đêm**: `motorbike_ocr_100` chỉ 116 ảnh ban ngày → **tự thu thêm test ban đêm**.
3. **Dataset màu gán nhãn**: chưa có; nhưng dùng `color_check.py` tự sinh nhãn màu yếu (weak label) từ crop biển đã có → tiết kiệm gán tay.
4. **Convert duydieu polygon→bbox** nếu dùng detector bbox thường.

**Feeds into:** Chương "Dữ liệu" (W2) — bảng inventory + license + quality thật; Detection (Nhật W3); OCR (Nhật W4); Màu biển (Đức W3); Phân loại xe (Nhật W5).
