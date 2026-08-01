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
| **vehicle_lmphmthanh** | [Kaggle lmphmthanh](https://www.kaggle.com/datasets/lmphmthanh/vietnam-vehicle-dataset) = mirror Roboflow `car-classification/vietnamese-vehicle v3` | Loại xe | **2.361** | YOLO bbox | nc=4 (12.163 box; 1=4.230, 0=3.960, 2=3.310, 3=663) | 640×640 | ⚠️ **Pretrain-only — cam giao thông TRÊN CAO, xe xa (xem §Filter khung hình). License CC BY 4.0 XÁC MINH** |
| **vehicle_cameraview** | [Kaggle haihovan](https://www.kaggle.com/datasets/haihovan/vietnam-vehicles-camera-view) | Loại xe (CCTV) | 156 | YOLO **pose** (kpt_shape[1,3]) | nc=4 car/motorcycle/truck/bus; lệch **bus=2.387**, moto=52 | 406×266, ngã tư Nov-2025 | ❌ **LOẠI — CCTV ngã tư đông, xe xa/nhỏ, lệch class** |
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

## §Filter khung hình — xe phải GẦN, rõ, đơn lẻ (yêu cầu triển khai bãi xe)

**Lý do:** camera bãi xe đặt góc tốt, xe cổng vào **gần** — không phải ảnh giao thông xa. Đo bằng `closeness.py` = tỉ lệ diện tích bbox/ảnh (YOLO w×h); "dominant" = box lớn nhất mỗi ảnh (chủ thể chính).

> **ĐÍNH CHÍNH (2026-07-30):** số duydieu ở bản đầu (28.8%/97.8%) **SAI** — `closeness.py` đọc nhầm polygon 4 điểm thành `w,h`. Bảng dưới đã tính lại đúng (`closeness2.py`) + xem ảnh thật. Chi tiết + bằng chứng: [[2026-07-30-vehicle-framing-report]].

| Dataset | Chỉ số đo (đúng) | Xem ảnh thật | Kết luận |
|---|---|---|---|
| **duydieu** (box=**biển**, polygon) | biển median **3.5%** khung | **ảnh CẬN 1 xe đơn lẻ** (ô tô/xe máy, sân/bãi) — biển nhỏ vì biển vốn nhỏ, nhưng **cả xe gần & rõ** | ✅ **HỢP cam cổng** (metric biển đo sai thứ; xe gần) |
| vehicle_lmphmthanh (box=xe) | dominant xe median 5.4%, close 32.7% | **cam trên cao nhìn xuống đường**, kể cả 16 ảnh gần nhất vẫn xa/xéo | ❌ street-view, không hợp cổng |
| vehicle_cameraview (box=xe) | dominant xe 3.0%, close 9.6% | CCTV ngã tư, xe li ti | ❌ FAR |
| plate_bomaich (box=biển) | biển median 4.7% | ảnh cảnh, xe cỡ vừa | (biển nhỏ là thường) |
| plate_tanhphp (box=biển) | biển median 1.4% | — | (box=biển, không suy ra độ gần xe) |

**Bài học đo lường:** với dataset **box=biển**, diện tích box KHÔNG phản ánh độ gần xe (biển luôn nhỏ). Phải **xem ảnh** — duydieu biển nhỏ nhưng xe cận.

**Bằng chứng ảnh** (vẽ bbox, ghi `domArea%`): `7_vehicle_lmphmthanh_NEAR.png` (gần nhất — vẫn cam đường trên cao), `8_vehicle_lmphmthanh_FAR.png` (đường trống, xe 0.2%), `9_vehicle_cameraview_NEAR.png` (ngã tư đông).

**Chốt sau filter (đã đính chính):**
1. Bộ **loại xe gán nhãn car/moto/truck/bus** công khai (lmphmthanh, cameraview) đều **street-view**, không hợp cổng bãi. **lmphmthanh nhãn số `0-3` nhập nhằng** (Roboflow trộn cả nhãn số lẫn tên) → không map tin cậy sang loại xe.
2. **NHƯNG `duydieu` LÀ ảnh cận 1 xe đơn lẻ** (ô tô/xe máy, sân bãi) — hợp góc cổng nhất; có nhãn **BSD/BSV** (biển dài≈ô tô / biển vuông≈xe máy, **verify aspect 2.53 vs 0.90**). Dùng proxy loại xe 2 lớp chính của bãi.
3. `vehicle_cameraview` **loại hẳn**; `vehicle_lmphmthanh` chỉ **pretrain hình dạng** (không tin nhãn).
4. Phân loại đầy đủ (tách truck/bus) → **tự thu data ở cổng bãi**.

## Ảnh mẫu đã xem (research/assets/dataset-samples/)

| File | Xác nhận trực quan |
|---|---|
| `1_bomaich_detect.png` | Cảnh đường/bãi VN: ô tô + xe máy, biển rõ |
| `2_motorbike_ocr.png` | Đuôi xe máy VN, **biển 2 hàng** trong bãi |
| `3_vehicle_roboflow.png` | Giao thông VN thật: bus/ô tô/xe máy/tải |
| `4_topkek_crops.png` | Biển VN crop: đọc được `60K-394.40`, `54-T5 4498`, `29A-974.35`; đủ màu trắng/đỏ/xanh/vàng, cả 1+2 hàng |
| `5_cameraview.png` | CCTV ngã tư VN (góc trên cao) |
| `6_chars.png` | Ký tự 28×28 tách sẵn |
| `7_vehicle_lmphmthanh_NEAR.png` | **Gần nhất** của bộ này — vẫn **cam giao thông trên cao**, xe xéo góc, không phải góc bãi |
| `8_vehicle_lmphmthanh_FAR.png` | Đường trống, xe li ti (domArea 0.2%) → chứng minh phần lớn xe xa |
| `9_vehicle_cameraview_NEAR.png` | CCTV ngã tư đông đúc, hàng chục xe nhỏ → FAR |

---

## Khuyến nghị CẬP NHẬT (sau kiểm tra thật)

| Module | Chốt dùng | Lý do (bằng chứng) |
|---|---|---|
| **Detect biển** | `plate_tanhphp` (2.255) + `plate_bomaich` (498) làm bbox; `duydieu` (4.578) cho **routing 1/2 hàng** | đã xác minh số ảnh + format; duydieu tách BSD/BSV = giải quyết luồng xe máy 2 hàng |
| **OCR** | `plate_ocr_topkek` (crop thật + label chuỗi) train chính; `motorbike_ocr_100` làm **test biển 2 hàng** | có sẵn cặp ảnh-chuỗi thật; tách synthetic khi đo |
| **Ký tự (nếu đi hướng char-classifier)** | `char_nguyenquanglinh` + augment lớp hiếm | lệch class đã đo, xử lý được |
| **Màu biển** | **HSV+CLAHE** (không cần CNN) | 4 màu tách được trên HSV, đo thật |
| **Loại xe** | **Tự thu ở bãi** (chính) + `duydieu` BSD/BSV proxy (ô tô/xe máy) + `vehicle_lmphmthanh` **pretrain-only** | §Filter khung hình: không bộ VN nào xe gần/rõ kiểu cam bãi; lmphmthanh là cam đường trên cao (xa); cameraview loại |
| **Loại/nguồn cần bổ sung** | Roboflow (cần API key), winter2897/trungdinh Drive, `ngkhtrf` | chưa tải đợt này |

## Còn thiếu → hành động
1. **ROBOFLOW_API_KEY** để tải bộ Roboflow gốc (8.397 ảnh school-fuhih) — nếu cần, cung cấp key.
2. **Biển 2 hàng ban đêm**: `motorbike_ocr_100` chỉ 116 ảnh ban ngày → **tự thu thêm test ban đêm**.
3. **Dataset màu gán nhãn**: chưa có; nhưng dùng `color_check.py` tự sinh nhãn màu yếu (weak label) từ crop biển đã có → tiết kiệm gán tay.
4. **Convert duydieu polygon→bbox** nếu dùng detector bbox thường.

**Feeds into:** Chương "Dữ liệu" (W2) — bảng inventory + license + quality thật; Detection (Nhật W3); OCR (Nhật W4); Màu biển (Đức W3); Phân loại xe (Nhật W5).
