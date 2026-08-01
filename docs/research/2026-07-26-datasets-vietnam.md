# Khảo sát dataset cho hệ thống bãi xe thông minh — ưu tiên Việt Nam

**Ngày tạo:** 2026-07-26
**Mode:** 3 (dataset research) + 2 (so sánh giải pháp OCR / màu biển)
**Mục đích:** chọn dataset và giải pháp cho 4 module: (1) phát hiện biển số, (2) đọc ký tự (OCR), (3) phân loại màu nền biển, (4) phân loại loại xe. Hệ thống **triển khai ở Việt Nam** → dữ liệu/biển/xe Việt Nam là ưu tiên trong mọi mục.

**Thứ tự trình bày:** nguồn Việt Nam trước, quốc tế sau (dùng cho transfer learning / augmentation).

**Cảnh báo xác minh:** các trang **Roboflow Universe trả HTTP 403** cho crawler → số ảnh lấy từ snippet kết quả tìm kiếm, **license từng project phải mở trang kiểm tra tay trước khi dùng** (Roboflow cho tác giả tự chọn license: hay gặp CC BY 4.0, một số Public Domain/MIT). Trang Kaggle load bằng JS → chi tiết class/size cần đăng nhập xem trực tiếp. Mọi số chưa mở được nguồn gốc đánh dấu **"chưa xác minh"**.

---

## Quy ước mức độ evidence

| Ký hiệu | Nghĩa |
|---|---|
| **Verified** | Đã mở trang gốc / README / license, số liệu lấy trực tiếp |
| **Snippet** | Số liệu từ snippet search engine, chưa mở trang gốc (Roboflow 403 / Kaggle JS) |
| **Chưa xác minh** | Chưa tiếp cận được, cần mở tay trước khi trích |

Mỗi dataset kèm 4 kiểm tra bắt buộc: **① Preprocessing · ② Standardisation (khi ghép nhiều nguồn) · ③ License · ④ Quality**.

---

# PART 1 — Dataset PHÁT HIỆN BIỂN SỐ (detect plate bounding box). Ưu tiên VN.

## 1.A Nguồn Việt Nam

### Bảng tổng hợp

| # | Dataset | Nguồn | Ảnh | Format | Loại biển | License | Ev. |
|---|---|---|---|---|---|---|---|
| D1 | vietnamese-license-plate (school-fuhih) | [Roboflow](https://universe.roboflow.com/school-fuhih/vietnamese-license-plate-tptd0) | **8.397** | YOLO/VOC/COCO export | biển VN (1+2 hàng, chưa tách rõ) | Roboflow — chưa xác minh | Snippet |
| D2 | Vietnam license-plate (Tran Ngoc Xuan Tin) | [Roboflow](https://universe.roboflow.com/tran-ngoc-xuan-tin-k15-hcm-dpuid/vietnam-license-plate-h8t3n) | 1.005 | export đa định dạng | VN | chưa xác minh | Snippet |
| D3 | Vietnam License Plate (Traffic Camera) | [Roboflow](https://universe.roboflow.com/traffic-camera/vietnam-license-plate-hayn8) | 885 | export đa định dạng | VN, ảnh camera giao thông | chưa xác minh | Snippet |
| D4 | vietnam-license-plate (Eric Nguyen) | [Roboflow](https://universe.roboflow.com/eric-nguyen-knfxn/vietnam-license-plate-curhr) | 350 | export đa định dạng | VN | chưa xác minh | Snippet |
| D5 | VNLicensePlate_yolov7 (bomaich) | [Kaggle](https://www.kaggle.com/datasets/bomaich/vnlicenseplate) | **1.000** | YOLO (xywh .txt), đã chia train/valid/test | VN | chưa xác minh (Kaggle) | Snippet |
| D6 | Vietnam License Plate Segment (duydieunguyen) | [Kaggle](https://www.kaggle.com/datasets/duydieunguyen/licenseplates) | chưa xác minh | segment/detection | VN | chưa xác minh | Snippet |
| D7 | Vietnamese License Plate Detection (miahuynh04) | [Kaggle](https://www.kaggle.com/datasets/miahuynh04/vietnamese-license-plate-detection) | chưa xác minh | detection | VN | chưa xác minh | Snippet |
| D8 | winter2897 Vietnamese Plate Dataset | [GitHub doc](https://github.com/winter2897/Real-time-Auto-License-Plate-Recognition-with-Jetson-Nano/blob/main/doc/dataset.md) | chưa nêu | **VOC + YOLO** (Google Drive), 2 bộ tách: detection & char-recognition | VN, có video đường phố VN để test | không nêu license rõ; ghi "thanks Mì Ai" | Verified (nội dung), license unclear |

**Ghi chú D8 (winter2897):** đây là **nguồn gốc** mà nhiều repo VN khác dùng lại (trungdinh22, Trung-Rei đều credit winter2897 + Mì Ai). Đã có trong `refs.bib`: `winter2897jetsonalpr`. Chia sẵn 2 task (detection / character), có cả VOC lẫn YOLO → tiện nhất để bắt đầu, nhưng **license không minh bạch** → dùng để train nội bộ, **không redistribute**.

### 4 kiểm tra — nhóm VN detection

**① Preprocessing:** cần resize về input model (640×640 cho YOLOv8/26), normalize [0,1]. Ảnh camera giao thông (D3) có thể mờ/nghiêng → thêm deskew ở bước cắt biển (xử lý ở pipeline, không ở dataset). Không cần OCR-level preprocessing ở giai đoạn detect.

**② Standardisation (ghép nhiều nguồn):** BẮT BUỘC nếu gộp D1–D8:
- Thống nhất **annotation format → YOLO txt** (D8/VOC cần convert VOC→YOLO; Roboflow export thẳng YOLO được).
- Thống nhất **1 class duy nhất** `license_plate` (hoặc 2 class `plate_1row`/`plate_2row` nếu muốn phân luồng sớm) — remap class-id giữa các nguồn.
- Chuẩn hóa kích thước ảnh khi train (YOLO tự letterbox 640), **không cần ép DPI** — YOLO detection bất biến DPI, chỉ cần đủ độ phân giải biển (~≥ 30px cao ký tự).
- **Khử trùng lặp giữa nguồn:** D8 và trungdinh22/Trung-Rei chia sẻ chung dữ liệu Mì Ai → **rủi ro leakage train/test cao**. Phải dedup bằng perceptual hash trước khi trộn.

**③ License:** Roboflow/Kaggle/GitHub đều **chưa xác minh** → xử lý an toàn: **train nội bộ đồ án, không phát hành lại dataset**. Ưu tiên các project ghi rõ CC BY 4.0/CC0. Nếu cần con số chắc chắn cho báo cáo, mở từng trang.

**④ Quality:** D1 (8.397 ảnh) là lớn nhất và có pretrained model → chất lượng khả dụng **Medium-High** nhưng phải kiểm class balance 1-hàng vs 2-hàng (xe máy VN chiếm đa số → dễ lệch về biển 2 hàng). D3 camera giao thông → nhiều biến thiên góc/sáng (tốt cho robust) nhưng nhãn có thể thô. D5 đã chia sẵn split → tiện, cần kiểm nhãn thủ công mẫu.

## 1.B Nguồn quốc tế (fallback pretrain / augmentation — KHÔNG phải biển VN)

| Dataset | Nguồn | Quy mô | License | Dùng làm gì |
|---|---|---|---|---|
| **CCPD** (Chinese City Parking) | [GitHub detectRecog/CCPD](https://github.com/detectRecog/CCPD) | ~250k+ ảnh, ECCV 2018 | **MIT** (thương mại OK) | pretrain detector, augment đa dạng góc/sáng; biển TQ 1 hàng ≠ VN |
| **UFPR-ALPR** (Brazil) | [GitHub raysonlaroca](https://github.com/raysonlaroca/ufpr-alpr-dataset) | 4.500 ảnh full-annotated | **Academic non-commercial**, bắt buộc cite Laroca 2018 (IJCNN) | tham khảo pipeline detect+recog xe/camera chuyển động |

**Vì sao vẫn hữu ích:** transfer learning — pretrain trên CCPD (MIT, tự do) rồi fine-tune trên dữ liệu VN giúp hội tụ nhanh + robust hơn khi dữ liệu VN ít. **Không dùng trực tiếp để đánh giá** vì định dạng biển khác.

**Cảnh báo license quốc tế:** UFPR-ALPR **cấm thương mại**, chỉ academic + phải trích dẫn → dùng được cho đồ án tốt nghiệp (academic) nhưng ghi rõ nguồn. CCPD MIT → thoải mái.

---

# PART 2 — Đọc ký tự (OCR / nhận dạng): so sánh GIẢI PHÁP + dataset

Đây là quyết định kiến trúc quan trọng nhất của module đọc biển. So sánh 5 hướng.

## 2.A Bảng so sánh giải pháp

| Giải pháp | Cơ chế | 2 hàng (xe máy) | Pi 5 (edge) | Cần data train | Ưu | Nhược |
|---|---|---|---|---|---|---|
| **A. PaddleOCR (PP-OCRv5)** | detect+rec text engine | Xử lý được (detect từng dòng text) | **Nhanh nhất trong nhóm engine**: Pi4 ~28s/ảnh cold, RAM ~950MB; PP-OCRv5 mobile nhẹ | Zero-shot dùng model latin (hỗ trợ **Tiếng Việt**), fine-tune tùy chọn | Có sẵn, đa ngôn ngữ 100+, chịu biển nghiêng tốt hơn EasyOCR, dict tùy biến + fine-tune | Nặng hơn giải pháp thuần YOLO-char; cần sắp xếp lại thứ tự dòng cho biển 2 hàng |
| **B. EasyOCR** | detect+rec (CRAFT+CRNN) | Được, cần logic ghép dòng | Chậm hơn Paddle: Pi4 ~51s/ảnh, RAM ~1.8GB → **rủi ro OOM trên Pi** | Zero-shot, có 'vi' | Dễ dùng, script nhanh | Chậm + ngốn RAM nhất → **kém phù hợp edge**; kém trên biển nghiêng |
| **C. OCR-as-detection (YOLO ký tự)** | YOLOv8/26 detect từng ký tự như 1 class (0-9, A-Z) | **Tốt nhất cho 2 hàng** nếu sort theo (y,x) | **Nhanh nhất**, dùng CHUNG detector đã có → 1 engine | Cần label ký tự (bounding box từng ký tự) | Không thêm dependency OCR; latency thấp; đúng hướng tran2025vietnamlpr & mrzaizai2k | Phải tự gán nhãn ký tự; kém khi ký tự dính/mờ; không đọc được ký tự lạ ngoài tập class |
| **D. CRNN + CTC (tự train)** | crop biển → sequence model | Cần tách 2 dòng trước | Nhẹ vừa, ONNX được | Cần nhiều ảnh biển + chuỗi label | Chính xác cao khi train đủ (dang2024vietnamcrnn) | Tốn công train + label chuỗi; tách 2 hàng thủ công |
| **E. fast-plate-ocr / FastALPR** | OCR nhẹ chuyên biển, ONNX | Model theo layout | **Rất nhanh** (CCT-xs ~3094 plates/s GPU; ONNX export TFLite/CoreML) | Có pretrained; fine-tune được | Thiết kế sẵn cho biển + edge (ONNX Runtime); [repo](https://github.com/ankandrew/fast-plate-ocr) | Pretrained chưa phủ biển VN 2 hàng → **cần fine-tune trên data VN** |

Nguồn: [PaddleOCR PP-OCRv5 multilingual (Vietnamese)](https://github.com/PaddlePaddle/PaddleOCR/blob/main/docs/version3.x/algorithm/PP-OCRv5/PP-OCRv5_multi_languages.en.md) · [Paddle vs Easy benchmark](https://tildalice.io/paddleocr-vs-easyocr-benchmark/) · [YOLOv8 + Easy/Paddle/Tesseract eval](https://www.researchgate.net/publication/385535133) · [fast-plate-ocr](https://github.com/ankandrew/fast-plate-ocr) · [FastALPR](https://github.com/ankandrew/fast-alpr).

## 2.B Có CẦN detect ký tự riêng không? (câu hỏi user)

**Không bắt buộc.** Hai trường phái:
- **Whole-plate string OCR** (A/B/E): cắt biển → đọc cả chuỗi. Ít công gán nhãn (chỉ cần chuỗi text, không cần box ký tự). Phù hợp khi dùng engine sẵn.
- **Char-detection** (C): detect từng ký tự. Cần gán nhãn box ký tự nhưng **tái dùng detector**, latency thấp nhất — hợp mục tiêu **< 2s/xe trên Pi 5**.

## 2.C Dataset ký tự VN (cho hướng C/D)

| Dataset | Nguồn | Nội dung | License |
|---|---|---|---|
| Character Dataset For VN License Plate | [Kaggle nguyenquanglinh0109](https://www.kaggle.com/datasets/nguyenquanglinh0109/character-dataset-for-vietnam-license-plate) | crop ký tự đơn, dùng train nhận dạng ký tự | chưa xác minh (Kaggle JS) |
| VN License Plate OCR | [Kaggle topkek69](https://www.kaggle.com/datasets/topkek69/vietnamese-license-plate-ocr) | ảnh biển + chuỗi label OCR | chưa xác minh |
| winter2897 char-recognition set | [GitHub](https://github.com/winter2897/Real-time-Auto-License-Plate-Recognition-with-Jetson-Nano/blob/main/doc/dataset.md) | box + class ký tự (VOC/YOLO) | không rõ, dùng nội bộ |

**4 kiểm tra — dataset ký tự:**
- **① Preprocessing:** crop theo box biển → deskew (Hough/perspective) → **CLAHE tăng tương phản** (quan trọng ban đêm) → resize chuẩn (vd 48×48/ký tự cho CRNN, hoặc giữ crop biển cho YOLO-char) → grayscale tùy model.
- **② Standardisation:** nếu trộn char-set nhiều nguồn phải **thống nhất tập class = 0-9 + A-Z** (bỏ I, O, Q nếu biển VN không dùng — kiểm quy chuẩn biển), map nhãn đồng nhất, cùng kích thước crop.
- **③ License:** Kaggle/GitHub chưa xác minh → train nội bộ.
- **④ Quality:** char dataset dễ lệch class (số 0/1/8 nhiều hơn chữ hiếm) → cần kiểm class balance + augment ký tự hiếm.

## 2.D Khuyến nghị OCR cho đồ án (edge, < 2s/xe)

1. **Baseline nhanh để chạy sớm:** **PaddleOCR PP-OCRv5 mobile (latin/vi)** zero-shot → có kết quả ngay tuần OCR (W4), nhẹ hơn EasyOCR, chịu nghiêng tốt.
2. **Hướng tối ưu edge (khuyến nghị chính):** **OCR-as-detection bằng YOLO ký tự (C)** — tái dùng detector, latency thấp nhất, đúng thực nghiệm VN (tran2025vietnamlpr, mrzaizai2k). Xử lý 2 hàng bằng sort (y,x) + ngưỡng phân dòng.
3. **Dự phòng độ chính xác:** fine-tune **fast-plate-ocr (E)** trên data VN nếu (C) yếu ở biển mờ.
4. **Loại EasyOCR khỏi edge** vì RAM ~1.8GB + chậm nhất trên Pi.

**Rủi ro:** biển xe máy 2 hàng + biển bẩn/nghiêng là điểm yếu chung → cần tập test riêng biển 2 hàng ban đêm để đo.

---

# PART 3 — Phân loại MÀU nền biển (module Đức)

Màu nền biển VN: **trắng** (cá nhân), **vàng** (kinh doanh/dịch vụ), **xanh dương** (cơ quan nhà nước), **đỏ** (quân đội), xanh lá (điện — mới). Đây là tín hiệu phân loại xe kinh doanh vs cá nhân → phục vụ logic phí.

## 3.A So sánh giải pháp

| Giải pháp | Cơ chế | Ánh sáng/đêm | Edge | Cần data | Ưu | Nhược |
|---|---|---|---|---|---|---|
| **HSV threshold + CLAHE** (kế hoạch) | chuyển HSV, ngưỡng Hue theo màu, CLAHE cân bằng sáng | CLAHE giúp; vẫn nhạy đèn vàng/ánh phản chiếu | **Rất nhẹ**, không cần train, ms-level | 0 (chỉ cần tune ngưỡng) | Đơn giản, minh bạch, không cần GPU | Ngưỡng cứng dễ nhầm trắng↔vàng nhạt dưới đèn; cần tune tay |
| **CNN nhỏ trên crop biển** | MobileNet/CNN 3-5 lớp phân loại màu | Robust hơn nếu train đủ đa sáng | Nhẹ (ONNX/quant), vẫn realtime Pi | Cần **crop biển gán nhãn màu** (tự label) | Bền với nhiễu sáng; học được sắc thái | Cần dataset + train; overkill nếu HSV đủ |
| **Dominant color / k-means** | cluster màu vùng nền biển | Nhạy sáng như HSV | Rất nhẹ | 0 | Không ngưỡng cứng từng màu | Nhạy vùng ký tự/viền; cần lọc nền |

Nguồn phương pháp color-based localization (HSV) + so sánh CNN: [Springer OpenCV LP HSV](https://link.springer.com/chapter/10.1007/978-981-99-1145-5_14) · [ScienceDirect CNN LP](https://www.sciencedirect.com/science/article/pii/S2590005620300254).

## 3.B Dataset màu

**Không có** dataset biển VN gán nhãn theo màu công khai đã xác minh → **team phải tự gán nhãn**: lấy crop biển từ Part 1, gán 1 nhãn màu/biển (white/yellow/blue/red/green). Vài trăm–1k crop/màu là đủ cho CNN nhỏ; HSV thì chỉ cần tập tune ngưỡng nhỏ.

## 3.C Khuyến nghị màu

- **Bắt đầu bằng HSV + CLAHE** (đúng kế hoạch, nhẹ, W3) — đủ cho 4 màu tương phản cao.
- **Nâng cấp CNN nhỏ** chỉ khi HSV nhầm trắng↔vàng dưới đèn đêm (đo trước, đừng tối ưu sớm).
- Chuẩn hóa: mọi crop biển về cùng không gian màu (BGR→HSV nhất quán), CLAHE trên kênh V (không trên toàn ảnh RGB).

---

# PART 4 — Dataset LOẠI XE (classification: car/motorbike/truck/bus). Ưu tiên VN.

VN xe máy chiếm đa số → **độ phủ xe máy là tiêu chí số 1**.

## 4.A Nguồn Việt Nam

| # | Dataset | Nguồn | Ảnh | Class | License | Ev. |
|---|---|---|---|---|---|---|
| V1 | Vietnamese vehicle (car-classification) | [Roboflow](https://universe.roboflow.com/car-classification/vietnamese-vehicle/dataset/3) | **1.547** | car, bus, truck, motorcycle | chưa xác minh (Roboflow 403) | Snippet |
| V2 | Vietnamese Vehicles Dataset (duongtran1909) | [Kaggle](https://www.kaggle.com/datasets/duongtran1909/vietnamese-vehicles-dataset) | ~4GB, day+night, HCM | xe phổ biến VN, có ảnh đêm | **CC0 Public Domain** | Snippet (license snippet) |
| V3 | Vietnamese Bike and Motorbike (nqa112) | [Kaggle](https://www.kaggle.com/datasets/nqa112/vietnamese-bike-and-motorbike) | chưa xác minh | bike vs motorbike (VN) | chưa xác minh | Snippet |

**V2 CC0** = nguồn sạch license nhất cho vehicle → ưu tiên, đặc biệt có **ảnh đêm HCM** (hợp cảnh bãi xe thực tế).

## 4.B Nguồn quốc tế

| Dataset | Ảnh | Class | License | Ghi chú |
|---|---|---|---|---|
| Car and Motorcycle Detection (aliff-haikal) | [Roboflow](https://universe.roboflow.com/aliff-haikal-ssf6d/car-and-motorcycle-detection-with-kaggle-dataset) 887 | car, motorcycle | chưa xác minh | bổ sung mẫu xe máy |
| vehicle-detection (lynkeus03) | [Roboflow](https://universe.roboflow.com/lynkeus03/vehicle-detection-by9xs) ~9.2k | car/bus/truck/motorbike | chưa xác minh | quy mô lớn, đa lớp |
| COCO (vehicle classes) | — | car, motorcycle, bus, truck | CC BY 4.0 | **domain gap**: xe máy COCO ≠ mật độ/kiểu VN → chỉ pretrain |

### 4 kiểm tra — vehicle datasets

**① Preprocessing:** resize 640, normalize. Ảnh đêm (V2) → CLAHE/augment sáng. Không cần DPI chuẩn.

**② Standardisation:** thống nhất **taxonomy class** giữa nguồn — VN cần tối thiểu `{motorbike, car, truck, bus}` (+ `bicycle` tùy). V3 (bike vs motorbike) phải map vào taxonomy chung. Convert hết về **YOLO txt**, remap class-id. Dedup ảnh trùng.

**③ License:** V2 **CC0 (tự do)** → an toàn nhất. Roboflow/các nguồn khác chưa xác minh → dùng nội bộ. COCO CC BY 4.0 (ghi nguồn).

**④ Quality:** phải kiểm **class balance nghiêng xe máy** (đúng thực tế VN nhưng gây bias — cần đủ mẫu car/truck/bus). V2 có day+night → tốt cho robust. Kiểm nhãn Roboflow mẫu vì nhãn cộng đồng đôi khi thô.

---

# Chuẩn hóa khi GHÉP nhiều dataset (standardisation plan)

Nếu trộn nhiều nguồn thành 1 tập train thống nhất:

| Yếu tố | Chuẩn đề xuất |
|---|---|
| **Annotation format** | **YOLO txt** (convert VOC/COCO→YOLO) cho detection & char; classification theo thư mục/label |
| **Kích thước train** | letterbox **640×640** (YOLOv8/26). Không ép DPI — chỉ đảm bảo biển đủ phân giải (ký tự ≥ ~30px) |
| **Không gian màu** | BGR nhất quán (OpenCV); CLAHE trên kênh V (HSV) cho tiền xử lý sáng |
| **Class taxonomy** | Plate detect: `license_plate` (hoặc `plate_1row`/`plate_2row`). Char: `0-9 + A-Z` (loại ký tự không xuất hiện trên biển VN). Vehicle: `motorbike, car, truck, bus (+bicycle)` |
| **Khử trùng lặp** | perceptual-hash dedup **BẮT BUỘC** (nhiều repo VN dùng chung data Mì Ai/winter2897 → tránh leakage train/test) |
| **Split** | chia train/val/test **sau khi dedup**, giữ tỉ lệ 1-hàng/2-hàng và ngày/đêm cân đối |

**Về DPI:** với detection/OCR dùng CNN, **DPI không quan trọng** — mô hình bất biến DPI, chỉ quan tâm độ phân giải pixel của biển/ký tự. Không cần chuẩn hóa DPI, chỉ cần lọc bỏ ảnh biển quá nhỏ/mờ.

---

# Bảng KHUYẾN NGHỊ tổng hợp

| Module | Primary | Augment/pretrain | Ghi chú |
|---|---|---|---|
| **Plate detection** | Roboflow D1 (8.397) + winter2897 D8 (VOC+YOLO, chia sẵn task) | CCPD (MIT) pretrain | dedup; verify license D1 trước khi trích báo cáo |
| **OCR** | **YOLO-char (C)** làm chính; PaddleOCR PP-OCRv5 (vi) làm baseline sớm | fast-plate-ocr fine-tune nếu cần | loại EasyOCR khỏi edge (RAM/chậm) |
| **Char data** | winter2897 char set + Kaggle char (nguyenquanglinh) | tự augment ký tự hiếm | class = 0-9+A-Z |
| **Màu biển** | **HSV + CLAHE** (kế hoạch) | CNN nhỏ nếu nhầm trắng↔vàng đêm | tự gán nhãn crop biển theo màu |
| **Vehicle type** | **Kaggle V2 (CC0, day+night HCM)** | COCO pretrain | motorbike-heavy, cân class car/truck/bus |

## Khoảng trống → team PHẢI tự thu thập / gán nhãn

1. **Dataset màu biển VN** — không có public → tự crop + gán nhãn màu.
2. **Biển 2 hàng xe máy ban đêm** — điểm yếu OCR, cần tự thu tập test riêng.
3. **License minh bạch** — phần lớn nguồn VN chưa rõ license → an toàn: chỉ train nội bộ đồ án, không redistribute; ưu tiên CC0/CC-BY (V2, CCPD) khi cần chắc chắn.
4. **Cân bằng loại xe** — dữ liệu VN nghiêng xe máy → bổ sung mẫu car/truck/bus.

---

**Feeds into:**
- Chương "Dữ liệu" (W2) — nguồn dataset, license, kế hoạch tự thu thập/gán nhãn, chuẩn hóa gộp nguồn.
- Module **Detection** (Nhật, W3) — chọn D1+D8, pretrain CCPD, taxonomy class.
- Module **OCR** (Nhật, W4) — quyết định YOLO-char vs PaddleOCR; dataset ký tự.
- Module **Màu biển** (Đức, W3) — HSV+CLAHE, tự gán nhãn màu.
- Module **Phân loại xe** (Nhật, W5) — Kaggle V2 CC0, cân bằng class.
