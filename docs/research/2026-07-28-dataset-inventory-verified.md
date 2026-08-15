# Dataset đã tải + kiểm tra thực tế (verified inventory)

**Ngày tạo:** 2026-07-28 | **Mode:** 3 (dataset)
**Mục đích:** mọi số liệu lấy từ tải thật + mở file thật (đếm ảnh, đọc annotation, đo kích thước, xem ảnh mẫu, phân tích HSV, thống kê class). Bằng chứng thực nghiệm cho [[2026-07-26-datasets-vietnam]].

**Công cụ:** Kaggle API tải trực tiếp; `inspect_ds.py` (đếm/format/dims/class), `color_check.py` (HSV), `montage.py` (lưới mẫu). Roboflow web 403 -> dùng mirror Kaggle. Ảnh mẫu: `research/assets/dataset-samples/`.
**Chưa tải:** Roboflow trực tiếp (cần `ROBOFLOW_API_KEY`); GitHub Drive (winter2897/trungdinh22); `ngkhtrf` (1GB, để dành dung lượng).

---

## Bảng tổng hợp đã kiểm tra thật

| Key | Nguồn | Module | Ảnh | Format | Class | Kích thước | Verdict |
|---|---|---|---|---|---|---|---|
| plate_tanhphp | [Kaggle tanhphp](https://www.kaggle.com/datasets/tanhphp/vietnamese-license-plates) | Detect biển | 2.255 | YOLO bbox | nc=1 `Bien-so` (2.998 box) | 144-2048px | [ưu tiên] Detect chính |
| plate_segment_duydieu | [Kaggle duydieunguyen](https://www.kaggle.com/datasets/duydieunguyen/licenseplates) | Detect + layout | 4.578 | YOLO-SEG (polygon 4 điểm) | nc=2: BSD(1 hàng)=1.641, BSV(2 hàng)=3.559 | 380-600px | [ưu tiên] Phân luồng 1/2 hàng + biển nghiêng |
| plate_bomaich_yolov7 | [Kaggle bomaich](https://www.kaggle.com/datasets/bomaich/vnlicenseplate) | Detect biển | 498 | YOLO bbox, split sẵn | nc=1 plate (780 box) | 571-1920px | [dùng] Bổ sung |
| plate_ocr_topkek | [Kaggle topkek69](https://www.kaggle.com/datasets/topkek69/vietnamese-license-plate-ocr) | OCR chuỗi | 12.190 (6.643 thật + 5.547 sinh) | crop + CSV `Name,Label,Type` | biển 1+2 hàng, type1-7 | 28-235px | [ưu tiên] OCR chính |
| motorbike_ocr_100 | [Kaggle dtkngan](https://www.kaggle.com/datasets/dtkngan/100-bien-so-xe-may-ocr) | OCR xe máy 2 hàng | 116 | ảnh + txt chuỗi biển | xe máy 2 hàng | 472×303 | [dùng] Test biển 2 hàng |
| char_nguyenquanglinh | [Kaggle nguyenquanglinh0109](https://www.kaggle.com/datasets/nguyenquanglinh0109/character-dataset-for-vietnam-license-plate) | Nhận dạng ký tự | 1.839 | folder=class | 0-9, A-Z (thiếu vài) + Noise | 28×28 | [điều kiện] Dùng có điều kiện (lệch class) |
| vehicle_lmphmthanh | [Kaggle lmphmthanh](https://www.kaggle.com/datasets/lmphmthanh/vietnam-vehicle-dataset) (mirror Roboflow `vietnamese-vehicle v3`) | Loại xe | 2.361 | YOLO bbox | nc=4 (12.163 box; id1=4.230, id0=3.960, id2=3.310, id3=663) | 640×640 | [điều kiện] Pretrain-only (cam trên cao, xe xa). License CC BY 4.0 xác minh |
| vehicle_cameraview | [Kaggle haihovan](https://www.kaggle.com/datasets/haihovan/vietnam-vehicles-camera-view) | Loại xe (CCTV) | 156 | YOLO pose | nc=4 car/moto/truck/bus; lệch bus=2.387, moto=52 | 406×266 | [loại] LOẠI (CCTV ngã tư, xe xa, lệch class) |
| ~~plate_unidpro~~ | [Kaggle unidpro](https://www.kaggle.com/datasets/unidpro/license-plate-detection-dataset) | - | 100 | folder=class | USA/Norway/Bahrain/Ireland | - | [loại] LOẠI (không phải VN) |
| ~~vehicle_hanoi~~ | [Kaggle thanhlamdev](https://www.kaggle.com/datasets/thanhlamdev/vehicle-at-ha-noi) | - | 0 | 2 CSV | khảo sát đi lại (25.591 dòng) | - | [loại] LOẠI (không có ảnh, tabular) |

Usability rating cao không đồng nghĩa hợp mục tiêu: `unidpro` (0.94) không phải VN; `vehicle_hanoi` (1.0) là CSV. Phải mở file mới biết.

---

## Phân tích màu biển (HSV, 599 crop thật topkek/cropped - mask chữ tối, lấy nền sáng)

| Màu | Số crop | Tỉ lệ | Ý nghĩa |
|---|---|---|---|
| Trắng | 372 | 62.1% | cá nhân |
| Vàng | 115 | 19.2% | kinh doanh/dịch vụ |
| Xanh dương | 57 | 9.5% | nhà nước |
| Đỏ | 37 | 6.2% | quân đội |
| Xanh lá | 3 | 0.5% | EV mới - quá hiếm để train |
| khác/tối | 15 | 2.5% | mờ/thiếu sáng |

1. Đủ 4 màu chính (trắng/vàng/xanh/đỏ) -> module màu có nghĩa.
2. 4 cụm hue/saturation tách rõ -> HSV+CLAHE khả thi, chưa cần CNN.
3. Lệch nặng về trắng (62%), xanh lá gần vắng -> CNN màu phải xử lý imbalance; HSV chỉ cần tune ngưỡng.
4. Cross-check duydieu (crop rộng) cho trắng 84% - sai lệch do lẫn nền; crop sát biển (topkek) đáng tin hơn.

---

## Vấn đề chất lượng (đo thật)

- **char_nguyenquanglinh lệch class nặng:** `M=4, Y=19, Z=32` vs `F=148, G=85, Noise=124`. Ký tự hiếm (M) gần như không train được -> augment mạnh/bổ sung. Lớp `Noise` (124) hữu ích lọc nhiễu.
- **duydieu = polygon 4 điểm** (không phải bbox): mỗi dòng `class + 8 tọa độ` = segmentation/oriented box -> cần YOLO-seg hoặc convert polygon->bbox.
- **vehicle_cameraview lệch class + pose:** bus=2.387 áp đảo, moto=52 (ngược thực tế VN) + keypoint -> không hợp làm data chính.
- **topkek trộn thật (6.643) + sinh (5.547):** tách generated/ khi đánh giá để tránh thổi phồng accuracy.
- **Không archive nào kèm LICENSE** trừ `vehicle_lmphmthanh` (`CC BY 4.0` trong data.yaml). Còn lại theo trang Kaggle -> train nội bộ, không phát hành.

---

## Filter khung hình - xe phải gần, rõ, đơn lẻ (yêu cầu bãi xe)

Camera bãi xe đặt góc tốt, xe cổng vào gần - không phải ảnh giao thông xa. Đo bằng `closeness.py` = tỉ lệ diện tích bbox/ảnh; "dominant" = box lớn nhất mỗi ảnh.

> **ĐÍNH CHÍNH (2026-07-30):** số duydieu bản đầu (28.8%/97.8%) SAI - `closeness.py` đọc nhầm polygon 4 điểm thành `w,h`. Bảng dưới tính lại đúng (`closeness2.py`) + xem ảnh. Chi tiết: [[2026-07-30-vehicle-framing-report]].

| Dataset | Chỉ số (đúng) | Ảnh thật | Kết luận |
|---|---|---|---|
| duydieu (box=biển, polygon) | biển median 3.5% | cận 1 xe đơn lẻ (ô tô/xe máy, sân bãi), xe gần & rõ | [dùng] Hợp cam cổng (biển nhỏ vì biển vốn nhỏ) |
| vehicle_lmphmthanh (box=xe) | dominant 5.4%, close 32.7% | cam trên cao nhìn xuống đường, cả 16 ảnh gần nhất vẫn xa/xéo | [loại] street-view |
| vehicle_cameraview (box=xe) | dominant 3.0%, close 9.6% | CCTV ngã tư, xe li ti | [loại] FAR |
| plate_bomaich (box=biển) | biển median 4.7% | ảnh cảnh, xe cỡ vừa | (biển nhỏ là thường) |
| plate_tanhphp (box=biển) | biển median 1.4% | - | (box=biển, không suy ra độ gần xe) |

Với dataset box=biển, diện tích box KHÔNG phản ánh độ gần xe (biển luôn nhỏ) -> phải xem ảnh. Bằng chứng: `7_vehicle_lmphmthanh_NEAR.png` (gần nhất vẫn cam trên cao), `8_..._FAR.png` (xe 0.2%), `9_vehicle_cameraview_NEAR.png` (ngã tư đông).

**Chốt sau filter:**
1. Bộ loại xe gán nhãn car/moto/truck/bus công khai (lmphmthanh, cameraview) đều street-view, không hợp cổng. lmphmthanh nhãn số 0-3 nhập nhằng -> không map tin cậy.
2. duydieu là ảnh cận 1 xe đơn lẻ, hợp góc cổng nhất; nhãn BSD/BSV (biển dài~ô tô / vuông~xe máy, verify aspect 2.53 vs 0.90) -> proxy loại xe 2 lớp.
3. vehicle_cameraview loại hẳn; lmphmthanh chỉ pretrain hình dạng.
4. Phân loại đầy đủ (tách truck/bus) -> tự thu ở cổng bãi.

---

## Khuyến nghị cập nhật

| Module | Chốt dùng | Lý do |
|---|---|---|
| Detect biển | `plate_tanhphp` (2.255) + `plate_bomaich` (498) bbox; `duydieu` (4.578) routing 1/2 hàng | verified số + format; duydieu tách BSD/BSV |
| OCR | `plate_ocr_topkek` chính; `motorbike_ocr_100` test 2 hàng | có cặp ảnh-chuỗi thật; tách synthetic khi đo |
| Ký tự (nếu char-classifier) | `char_nguyenquanglinh` + augment lớp hiếm | lệch class đã đo |
| Màu biển | HSV+CLAHE (không cần CNN) | 4 màu tách trên HSV |
| Loại xe | Tự thu ở bãi (chính) + `duydieu` BSD/BSV proxy + `lmphmthanh` pretrain-only | không bộ VN nào xe gần/rõ kiểu cam bãi |

**Còn thiếu -> hành động:**
1. `ROBOFLOW_API_KEY` để tải bộ Roboflow gốc (8.397 school-fuhih).
2. Biển 2 hàng ban đêm: `motorbike_ocr_100` chỉ 116 ảnh ban ngày -> tự thu test đêm.
3. Dataset màu: dùng `color_check.py` sinh weak label màu từ crop có sẵn.
4. Convert duydieu polygon->bbox nếu dùng detector bbox thường.

**Feeds into:** Chương Dữ liệu (W2); Detection (Nhật W3); OCR (Nhật W4); Màu biển (Đức W3); Phân loại xe (Nhật W5).
