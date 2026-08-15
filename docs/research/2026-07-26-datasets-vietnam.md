# Khảo sát dataset hệ thống bãi xe thông minh - ưu tiên Việt Nam

**Ngày tạo:** 2026-07-26 | **Mode:** 3 (dataset) + 2 (so sánh giải pháp OCR/màu biển)
**Mục đích:** chọn dataset + giải pháp cho 4 module: (1) phát hiện biển số, (2) OCR, (3) phân loại màu nền biển, (4) phân loại loại xe. Triển khai tại VN -> ưu tiên dữ liệu/biển/xe VN, quốc tế dùng cho transfer learning.

**Xác minh:** Roboflow Universe trả HTTP 403 cho crawler -> số ảnh lấy từ snippet, license phải mở trang kiểm tra tay trước khi dùng. Kaggle load JS -> chi tiết cần đăng nhập. Số chưa mở được nguồn đánh dấu "chưa xác minh".

| Ký hiệu evidence | Nghĩa |
|---|---|
| Verified | Đã mở trang gốc/README/license, số liệu trực tiếp |
| Snippet | Số liệu từ snippet search, chưa mở nguồn |
| Chưa xác minh | Chưa tiếp cận được |

Mỗi dataset kiểm 4 mục khi ghép nguồn: (1) Preprocessing | (2) Standardisation | (3) License | (4) Quality.

---

## Part 1 - Phát hiện biển số (bbox)

### 1.A Nguồn VN

| # | Dataset | Nguồn | Ảnh | Format | Loại biển | License | Ev. |
|---|---|---|---|---|---|---|---|
| D1 | vietnamese-license-plate (school-fuhih) | [Roboflow](https://universe.roboflow.com/school-fuhih/vietnamese-license-plate-tptd0) | 8.397 | YOLO/VOC/COCO | VN (1+2 hàng, chưa tách) | chưa xác minh | Snippet |
| D2 | Vietnam license-plate (Tran Ngoc Xuan Tin) | [Roboflow](https://universe.roboflow.com/tran-ngoc-xuan-tin-k15-hcm-dpuid/vietnam-license-plate-h8t3n) | 1.005 | đa định dạng | VN | chưa xác minh | Snippet |
| D3 | Vietnam License Plate (Traffic Camera) | [Roboflow](https://universe.roboflow.com/traffic-camera/vietnam-license-plate-hayn8) | 885 | đa định dạng | VN, camera giao thông | chưa xác minh | Snippet |
| D4 | vietnam-license-plate (Eric Nguyen) | [Roboflow](https://universe.roboflow.com/eric-nguyen-knfxn/vietnam-license-plate-curhr) | 350 | đa định dạng | VN | chưa xác minh | Snippet |
| D5 | VNLicensePlate_yolov7 (bomaich) | [Kaggle](https://www.kaggle.com/datasets/bomaich/vnlicenseplate) | 1.000 | YOLO xywh, đã split | VN | chưa xác minh | Snippet |
| D6 | Vietnam License Plate Segment (duydieunguyen) | [Kaggle](https://www.kaggle.com/datasets/duydieunguyen/licenseplates) | chưa xác minh | segment/detection | VN | chưa xác minh | Snippet |
| D7 | Vietnamese LP Detection (miahuynh04) | [Kaggle](https://www.kaggle.com/datasets/miahuynh04/vietnamese-license-plate-detection) | chưa xác minh | detection | VN | chưa xác minh | Snippet |
| D8 | winter2897 Vietnamese Plate | [GitHub](https://github.com/winter2897/Real-time-Auto-License-Plate-Recognition-with-Jetson-Nano/blob/main/doc/dataset.md) | chưa nêu | VOC + YOLO, tách 2 task | VN, có video test | không rõ | Verified nội dung |

**D8:** nguồn gốc mà nhiều repo VN dùng lại (trungdinh22, Trung-Rei credit winter2897 + Mì Ai). Đã có trong `refs.bib`: `winter2897jetsonalpr`. Tách sẵn detection/character, có cả VOC+YOLO -> tiện bắt đầu, license không minh bạch -> train nội bộ, không redistribute.

**4 kiểm tra:**
- (1) Resize 640×640, normalize [0,1]. Deskew xử lý ở pipeline cắt biển, không ở dataset.
- (2) Nếu gộp D1-D8: thống nhất annotation -> YOLO txt (convert VOC), 1 class `license_plate` (hoặc `plate_1row`/`plate_2row`), letterbox 640. **Dedup perceptual-hash bắt buộc** - D8 và trungdinh22/Trung-Rei chung data Mì Ai -> rủi ro leakage cao.
- (3) Đều chưa xác minh -> train nội bộ, không phát hành.
- (4) D1 lớn nhất + có pretrained -> khả dụng, phải kiểm class balance 1-hàng/2-hàng. D3 camera -> nhiều biến thiên góc/sáng, nhãn thô. D5 đã split.

### 1.B Nguồn quốc tế (pretrain/augment, KHÔNG phải biển VN)

| Dataset | Nguồn | Quy mô | License | Dùng làm gì |
|---|---|---|---|---|
| CCPD (Chinese City Parking) | [GitHub](https://github.com/detectRecog/CCPD) | ~250k+, ECCV 2018 | MIT | pretrain detector, augment góc/sáng |
| UFPR-ALPR (Brazil) | [GitHub](https://github.com/raysonlaroca/ufpr-alpr-dataset) | 4.500 full-annotated | Academic non-commercial, cite Laroca 2018 | tham khảo pipeline detect+recog |

Pretrain CCPD (MIT) -> fine-tune data VN: hội tụ nhanh + robust hơn khi data VN ít. Không dùng đánh giá vì định dạng biển khác.

---

## Part 2 - OCR: so sánh giải pháp + dataset

### 2.A So sánh 5 giải pháp

| Giải pháp | Cơ chế | 2 hàng | Pi 5 edge | Data train | Nhược chính |
|---|---|---|---|---|---|
| A. PaddleOCR PP-OCRv5 | detect+rec engine | được (detect từng dòng) | nhanh nhất nhóm engine: Pi4 ~28s cold, RAM ~950MB | zero-shot latin/vi, fine-tune tùy chọn | nặng hơn YOLO-char; cần sắp lại thứ tự dòng |
| B. EasyOCR | CRAFT+CRNN | được, cần ghép dòng | Pi4 ~51s, RAM ~1.8GB -> rủi ro OOM | zero-shot 'vi' | chậm + ngốn RAM nhất; kém biển nghiêng |
| C. OCR-as-detection (YOLO ký tự) | YOLO detect từng ký tự | tốt nhất nếu sort (y,x) | nhanh nhất, dùng chung detector | cần label box ký tự | tự gán nhãn; kém khi ký tự dính/mờ |
| D. CRNN + CTC (tự train) | crop -> sequence | cần tách 2 dòng trước | nhẹ vừa, ONNX | cần nhiều ảnh + chuỗi label | tốn công train/label |
| E. fast-plate-ocr / FastALPR | OCR nhẹ chuyên biển, ONNX | theo layout | rất nhanh (CCT-xs ~3094 plates/s GPU) | có pretrained, fine-tune | pretrained chưa phủ biển VN 2 hàng |

Nguồn: [PP-OCRv5 multilingual](https://github.com/PaddlePaddle/PaddleOCR/blob/main/docs/version3.x/algorithm/PP-OCRv5/PP-OCRv5_multi_languages.en.md) | [Paddle vs Easy benchmark](https://tildalice.io/paddleocr-vs-easyocr-benchmark/) | [fast-plate-ocr](https://github.com/ankandrew/fast-plate-ocr) | [FastALPR](https://github.com/ankandrew/fast-alpr).

**Detect ký tự riêng có bắt buộc không?** Không. Whole-plate OCR (A/B/E) chỉ cần label chuỗi; char-detection (C) cần box ký tự nhưng tái dùng detector, latency thấp nhất -> hợp mục tiêu < 2s/xe.

### 2.B Dataset ký tự VN (hướng C/D)

| Dataset | Nguồn | Nội dung | License |
|---|---|---|---|
| Character Dataset For VN LP | [Kaggle](https://www.kaggle.com/datasets/nguyenquanglinh0109/character-dataset-for-vietnam-license-plate) | crop ký tự đơn | chưa xác minh |
| VN License Plate OCR | [Kaggle](https://www.kaggle.com/datasets/topkek69/vietnamese-license-plate-ocr) | ảnh biển + chuỗi label | chưa xác minh |
| winter2897 char-recognition | [GitHub](https://github.com/winter2897/Real-time-Auto-License-Plate-Recognition-with-Jetson-Nano/blob/main/doc/dataset.md) | box + class ký tự (VOC/YOLO) | không rõ |

**4 kiểm tra:** (1) crop -> deskew -> CLAHE (kênh V, quan trọng ban đêm) -> resize; (2) class = 0-9 + A-Z (bỏ ký tự không có trên biển VN); (3) train nội bộ; (4) char lệch class (0/1/8 nhiều) -> augment ký tự hiếm.

### 2.C Khuyến nghị OCR (edge, < 2s/xe)

1. Baseline sớm (W4): PaddleOCR PP-OCRv5 mobile (latin/vi) zero-shot.
2. Tối ưu edge (chính): OCR-as-detection YOLO ký tự (C) - tái dùng detector, latency thấp, đúng tran2025vietnamlpr/mrzaizai2k. 2 hàng xử lý sort (y,x) + ngưỡng phân dòng.
3. Dự phòng: fine-tune fast-plate-ocr (E) nếu (C) yếu ở biển mờ.
4. Loại EasyOCR khỏi edge (RAM + chậm).

Điểm yếu chung: biển 2 hàng + bẩn/nghiêng -> cần tập test riêng biển 2 hàng ban đêm.

---

## Part 3 - Phân loại màu nền biển (Đức)

Màu biển VN: trắng (cá nhân), vàng (kinh doanh), xanh dương (nhà nước), đỏ (quân đội), xanh lá (điện - mới). Phân biệt xe kinh doanh vs cá nhân -> phục vụ logic phí.

| Giải pháp | Cơ chế | Đêm | Edge | Data | Nhược |
|---|---|---|---|---|---|
| HSV threshold + CLAHE (kế hoạch) | ngưỡng Hue + CLAHE | CLAHE giúp, vẫn nhạy đèn vàng | rất nhẹ, ms-level | 0 | ngưỡng cứng nhầm trắng/vàng nhạt |
| CNN nhỏ trên crop biển | MobileNet/CNN 3-5 lớp | robust nếu train đủ | nhẹ (ONNX/quant) | cần crop gán nhãn màu | cần train; overkill nếu HSV đủ |
| Dominant color / k-means | cluster màu nền | nhạy sáng như HSV | rất nhẹ | 0 | nhạy vùng ký tự/viền |

Nguồn: [Springer OpenCV LP HSV](https://link.springer.com/chapter/10.1007/978-981-99-1145-5_14) | [ScienceDirect CNN LP](https://www.sciencedirect.com/science/article/pii/S2590005620300254).

**Dataset màu:** không có dataset biển VN gán màu công khai -> tự crop từ Part 1, gán 1 nhãn màu/biển. Vài trăm-1k crop/màu đủ cho CNN nhỏ; HSV chỉ cần tập tune ngưỡng nhỏ.

**Khuyến nghị:** bắt đầu HSV + CLAHE (W3, đủ cho 4 màu tương phản cao); nâng CNN nhỏ chỉ khi HSV nhầm trắng/vàng dưới đèn đêm (đo trước). CLAHE trên kênh V, không trên RGB.

---

## Part 4 - Phân loại loại xe (car/motorbike/truck/bus). Ưu tiên VN.

VN xe máy đa số -> độ phủ xe máy là tiêu chí số 1.

### 4.A Nguồn VN

| # | Dataset | Nguồn | Ảnh | Class | License | Ev. |
|---|---|---|---|---|---|---|
| V1 | Vietnamese vehicle (car-classification) | [Roboflow](https://universe.roboflow.com/car-classification/vietnamese-vehicle/dataset/3) | 1.547 | car, bus, truck, motorcycle | chưa xác minh | Snippet |
| V2 | Vietnamese Vehicles (duongtran1909) | [Kaggle](https://www.kaggle.com/datasets/duongtran1909/vietnamese-vehicles-dataset) | ~4GB, day+night HCM | xe phổ biến VN, có ảnh đêm | CC0 | Snippet |
| V3 | Vietnamese Bike and Motorbike (nqa112) | [Kaggle](https://www.kaggle.com/datasets/nqa112/vietnamese-bike-and-motorbike) | chưa xác minh | bike vs motorbike | chưa xác minh | Snippet |

V2 CC0 = license sạch nhất, có ảnh đêm HCM (hợp cảnh bãi xe) -> ưu tiên.

### 4.B Nguồn quốc tế

| Dataset | Nguồn | Ảnh | Class | License |
|---|---|---|---|---|
| Car and Motorcycle Detection | [Roboflow](https://universe.roboflow.com/aliff-haikal-ssf6d/car-and-motorcycle-detection-with-kaggle-dataset) | 887 | car, motorcycle | chưa xác minh |
| vehicle-detection (lynkeus03) | [Roboflow](https://universe.roboflow.com/lynkeus03/vehicle-detection-by9xs) | ~9.2k | car/bus/truck/motorbike | chưa xác minh |
| COCO (vehicle classes) | - | - | car, motorcycle, bus, truck | CC BY 4.0 |

COCO: domain gap (xe máy COCO khác mật độ/kiểu VN) -> chỉ pretrain.

**4 kiểm tra:** (1) resize 640, ảnh đêm V2 -> CLAHE/augment; (2) taxonomy tối thiểu `{motorbike, car, truck, bus}`, V3 map vào taxonomy chung, convert YOLO txt, dedup; (3) V2 CC0 an toàn nhất, COCO CC BY (ghi nguồn), khác chưa xác minh; (4) class balance nghiêng xe máy -> bổ sung car/truck/bus, kiểm nhãn Roboflow mẫu.

---

## Chuẩn hóa khi ghép nguồn

| Yếu tố | Chuẩn |
|---|---|
| Annotation | YOLO txt (convert VOC/COCO); classification theo thư mục |
| Kích thước train | letterbox 640×640. Không ép DPI - chỉ đảm bảo ký tự >= ~30px |
| Không gian màu | BGR (OpenCV); CLAHE kênh V (HSV) |
| Taxonomy | Plate: `license_plate` (hoặc `plate_1row`/`plate_2row`). Char: 0-9 + A-Z. Vehicle: motorbike/car/truck/bus (+bicycle) |
| Dedup | perceptual-hash BẮT BUỘC (nhiều repo dùng chung data Mì Ai/winter2897 -> leakage) |
| Split | chia sau dedup, giữ tỉ lệ 1-hàng/2-hàng + ngày/đêm cân đối |

DPI không quan trọng với CNN detection/OCR - chỉ cần độ phân giải pixel đủ, lọc ảnh biển quá nhỏ/mờ.

---

## Khuyến nghị tổng hợp

| Module | Primary | Augment/pretrain | Ghi chú |
|---|---|---|---|
| Plate detection | D1 (8.397) + D8 (VOC+YOLO) | CCPD (MIT) | dedup; verify license D1 trước khi trích |
| OCR | YOLO-char (C) chính; PP-OCRv5 (vi) baseline | fast-plate-ocr fine-tune nếu cần | loại EasyOCR khỏi edge |
| Char data | winter2897 + Kaggle char | augment ký tự hiếm | class 0-9+A-Z |
| Màu biển | HSV + CLAHE | CNN nhỏ nếu nhầm trắng/vàng đêm | tự gán nhãn crop |
| Vehicle type | V2 (CC0, day+night HCM) | COCO pretrain | cân class car/truck/bus |

**Khoảng trống -> tự thu/gán nhãn:**
1. Dataset màu biển VN - không có public.
2. Biển 2 hàng xe máy ban đêm - điểm yếu OCR, cần test set riêng.
3. License - phần lớn nguồn VN chưa rõ -> train nội bộ; ưu tiên CC0/CC-BY khi cần chắc.
4. Cân bằng loại xe - data VN nghiêng xe máy.

**Feeds into:** Chương Dữ liệu (W2); Detection (Nhật W3); OCR (Nhật W4); Màu biển (Đức W3); Phân loại xe (Nhật W5).
