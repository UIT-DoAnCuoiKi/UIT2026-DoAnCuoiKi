# Khảo sát: Các hệ thống quản lý bãi xe thông minh và dashboard tương tự

**Ngày tạo:** 2026-07-19 · **Pass 2 (đào sâu primary source):** 2026-07-21
**Mode:** 1 (literature review) + 2 (so sánh tech/product)
**Mục đích:** (1) Tài liệu related-work cho Chương "Tổng quan"; (2) số liệu baseline cho chương evaluation tuần 9; (3) tham khảo feature cho module dashboard React.

**Thứ tự:** Nguồn Việt Nam đứng trước trong mỗi mục (cùng định dạng biển số, cùng thị trường, cùng quy định → mặt bằng so sánh gần nhất), rồi đến nguồn quốc tế.

**Hệ thống của mình (khung so sánh):** YOLOv8/YOLO26 detect xe + biển số VN → PaddleOCR/EasyOCR → phân loại màu biển bằng HSV+CLAHE (trắng=tư nhân, vàng=kinh doanh, xanh=cơ quan) → FastAPI + PostgreSQL khớp session vào/ra + tính phí → dashboard React → edge Raspberry Pi 5, ONNX INT8, mục tiêu < 2 s/xe.

---

## Quy ước mức độ evidence

Mỗi entry ghi rõ mình đọc được đến đâu — quan trọng khi trích dẫn vào đồ án:

| Ký hiệu | Nghĩa | Cách dùng khi viết đồ án |
|---|---|---|
| ✅ **FULL** | Đã đọc full text (PDF/HTML), số liệu lấy từ bảng gốc | Trích dẫn tự tin, có thể dẫn số cụ thể + protocol |
| ⚠️ **ABSTRACT** | Chỉ abstract + metadata Crossref | Trích được headline number, **không** trích chi tiết protocol |
| 🔒 **PAYWALL** | Không truy cập được full text | Ghi rõ "theo abstract"; lấy PDF qua thư viện UIT trước khi nộp |

Metadata (tác giả, trang, DOI) của mọi entry đã verify qua **Crossref API** ngày 2026-07-21 — không lấy từ trí nhớ hay blog.

---

## A. Hệ thống học thuật

### A1. Nhận dạng biển số Việt Nam — related work ưu tiên cao nhất

---

#### A1.1 · Tran & Bui 2025 — LPR Việt Nam trên Raspberry Pi 4 🔒 **PAYWALL**

> **Baseline quan trọng nhất của đồ án: cùng biển số VN + cùng lớp phần cứng (Raspberry Pi).**

| Mục | Nội dung |
|---|---|
| **Trích dẫn** | V. Tran and T. Bui, "Implementation of a License Plate Recognition System in Vietnam Using Embedding Devices," in *Multi-disciplinary Trends in Artificial Intelligence (MIWAI 2024)*, Lecture Notes in Computer Science, Springer, Singapore, 2025, pp. 231–243. |
| **DOI / link** | [10.1007/978-981-96-0695-5_19](https://link.springer.com/chapter/10.1007/978-981-96-0695-5_19) · [mirror ACM DL](https://dl.acm.org/doi/abs/10.1007/978-981-96-0695-5_19) |
| **Tác giả (verified)** | Vanha Tran; Thiloan Bui — xác nhận qua Crossref 2026-07-21 |
| **Kiến trúc** | 2 giai đoạn: **SSD-MobileNetV2** detect biển số → **YOLOv8-nano** nhận dạng ký tự (OCR-as-detection, không dùng OCR engine) |
| **Phần cứng** | Raspberry Pi 4 Model B + Pi Camera V2 (8 MP) |
| **Số liệu** | Accuracy nhận dạng TB **95.68%**; thời gian xử lý TB **0.478 s/ảnh** |
| **Code** | Không công bố |
| **Trạng thái nguồn** | 🔒 Springer chặn crawl (HTTP 303 → IdP). Semantic Scholar/ResearchGate không có abstract. **Số liệu ở mức thứ cấp.** |

**⚠️ Cảnh báo khi dùng làm baseline:** chưa verify được (a) accuracy tính ở cấp ký tự hay cấp biển số, (b) cỡ tập test, (c) 0.478 s là chỉ inference hay cả I/O camera, (d) tỷ lệ biển 1 hàng (ô tô) vs 2 hàng (xe máy). **Bốn thông tin này quyết định việc so sánh có công bằng không** → phải lấy PDF qua thư viện UIT trước tuần 9.

**So với hệ thống mình:** họ dừng ở nhận dạng; mình cộng thêm phân loại màu biển, session vào/ra, tính phí, dashboard. Pi 5 nhanh hơn Pi 4 ~2–3× → nếu pipeline mình đạt < 2 s/xe end-to-end thì hợp lý so với 0.478 s/ảnh (chỉ nhận dạng) của họ. **BibTeX:** `tran2025vietnamlpr`

---

#### A1.2 · Dang và cộng sự 2024 — CRNN + attention, dataset bãi xe trong nhà ở VN ⚠️ **ABSTRACT**

> **Bổ sung pass 2. Đây là paper VN sát use-case bãi xe nhất — dataset thu tại bãi đỗ trong nhà.**

| Mục | Nội dung |
|---|---|
| **Trích dẫn** | L. T. A. Dang, V. D. Ngoc, P. C. L. T. Vu, N. N. Truong, P. T. Bao, and T. D. Trinh, "Vietnam Vehicle Number Recognition Based on an Improved CRNN with Attention Mechanism," *Int. J. Intelligent Transportation Systems Research*, vol. 22, pp. 374–389, 2024. |
| **DOI / link** | [10.1007/s13177-024-00402-7](https://link.springer.com/article/10.1007/s13177-024-00402-7) · [TRID](https://trid.trb.org/View/2414278) |
| **Nhóm** | Nhóm VN (Pham The Bao — Saigon University); công bố 31/5/2024; 7 citation (Semantic Scholar, 2026-07-21) |
| **Kiến trúc** | 3 bước: **YOLO** detect xe → **WPOD-NET** trích biển số (chuyên xử lý biển xiên góc) → **CRNN cải tiến** train đồng thời **CTC + attention** để đọc ký tự |
| **Dataset** | Tự thu tại **bãi đỗ xe trong nhà** ở VN (không công bố cỡ trong abstract) |
| **Số liệu** | **Word Error Rate (WER) = 0.014** trong tác vụ OCR |
| **Trạng thái nguồn** | ⚠️ Springer paywall; abstract lấy qua search index + Crossref metadata |

**So với hệ thống mình:** WPOD-NET là **lựa chọn thay thế đáng cân nhắc cho bước skew correction** trong `alpr-pipeline` của mình (mình đang định tự làm nắn phối cảnh). Việc họ dùng WER thay vì accuracy là một metric bổ sung mình nên báo cáo — WER phạt theo ký tự, so sánh được giữa các độ dài biển khác nhau. **BibTeX:** `dang2024vietnamcrnn`

---

#### A1.3 · Le và cộng sự 2023 — biển số xe máy VN, YOLOv8 3 tầng 🔒 **PAYWALL**

| Mục | Nội dung |
|---|---|
| **Trích dẫn** | D. H. Le, D. Mazumder, L.-D. Quach, S. Banerjee, and V.-D. Nguyen, "Robust Vietnam's Motorcycle License Plate Detection and Recognition Using Deep Learning Model," in *Future Data and Security Engineering (FDSE 2023)*, CCIS, Springer, Singapore, 2023, pp. 64–75. |
| **DOI / link** | [10.1007/978-981-99-8296-7_5](https://link.springer.com/chapter/10.1007/978-981-99-8296-7_5) |
| **Tác giả (verified)** | Duc Hoa Le; Debarshi Mazumder; Luyl-Da Quach; Shreya Banerjee; Vinh Dinh Nguyen — Crossref 2026-07-21 |
| **Kiến trúc** | YOLOv8 **3 tầng**: detect xe máy → detect biển số **bên trong bbox xe máy** → nhận dạng biển |
| **Dataset** | Dataset biển số xe máy VN trên Roboflow |
| **Số liệu** | **mAP 93%** (tốt nhất, sau 300 epoch). Không có số liệu tốc độ. |
| **Ứng dụng đích** | Phạt nguội vi phạm tốc độ |

**So với hệ thống mình:** đây là **baseline mAP trực tiếp cho biển 2 hàng xe máy VN** — loại biển khó nhất của mình. Cascade xe-trước-biển-sau của họ đúng bằng thiết kế `alpr-pipeline` của mình → xác nhận lựa chọn kiến trúc. Con số 93% mAP là mốc detection tuần 3 mình cần đạt hoặc vượt. **BibTeX:** `le2023motorcycleplate`

---

#### A1.4 · Tran-Anh và cộng sự 2023 — LPR đa góc nhìn (PTIT) ⚠️ **ABSTRACT** (arXiv mở)

| Mục | Nội dung |
|---|---|
| **Trích dẫn** | D. Tran-Anh, K. L. Tran, and H.-N. Vu, "License Plate Recognition Based On Multi-Angle View Model," arXiv:2309.12972, 2023. |
| **Link** | [arXiv:2309.12972](https://arxiv.org/abs/2309.12972) — truy cập tự do |
| **Kiến trúc** | Fuse đặc trưng corner-point/diện tích qua **3 góc nhìn** trước khi nhận dạng bằng **CnOCR** |
| **Dataset** | **PTITPlates** (tự thu, Học viện PTIT) + Stanford Cars |
| **Số liệu** | ⚠️ Abstract khẳng định vượt trội nhưng **không công bố con số headline** → không dùng làm baseline định lượng được |

**So với hệ thống mình:** giá trị chính là **related work nhóm VN** cho Tổng quan + ý tưởng đa góc nhìn. Vấn đề robust theo góc chụp mà họ giải bằng multi-view, mình giải một phần từ phía ánh sáng bằng HSV+CLAHE. **BibTeX:** `trananh2023multiangle`

---

#### A1.5 · UIT MAPR 2018 — Cuộc thi nhận dạng biển số xe máy VN

| Mục | Nội dung |
|---|---|
| **Nguồn** | MAPR 2018 organizers, "Vietnamese Bike License Plate Recognition Challenge," 1st Int. Conf. on Multimedia Analysis and Pattern Recognition, UIT, 2018. [mapr.uit.edu.vn](https://mapr.uit.edu.vn/2018/vietnamese-bike-license-plate-recognition) |
| **Dataset** | **3.000 ảnh xe máy chụp tại bãi giữ xe khách sạn ở VN** — 2.000 train / 1.000 test |
| **Task** | Detect biển số (bbox) + nhận dạng text |
| **Trạng thái** | ⚠️ Link download ghi "update soon" — **link cũ tính đến 2026-07-19, coi như không lấy được** |

**So với hệ thống mình:** xác lập gốc gác UIT trong Tổng quan (điểm cộng khi bảo vệ). **Không plan dùng dataset này cho tuần 2.** **BibTeX:** `mapr2018challenge`

---

### A2. Hệ thống bãi xe / ALPR quốc tế — full pipeline

---

#### A2.1 · Pradhan và cộng sự 2025 — bãi xe IoT + ALPR + thanh toán trên Raspberry Pi ✅ **FULL**

> **Bản sao gần nhất ở mức hệ thống của đồ án mình: edge Pi + ALPR + khớp session + tính phí + occupancy.**

| Mục | Nội dung |
|---|---|
| **Trích dẫn** | G. Pradhan, M. R. Prusty, V. S. Negi, and S. Chinara, "Advanced IoT-integrated parking systems with automated license plate recognition and payment management," *Scientific Reports*, vol. 15, art. 2388, 2025. |
| **DOI / link** | [10.1038/s41598-025-86441-w](https://www.nature.com/articles/s41598-025-86441-w) · **full text mở:** [PMC11742719](https://pmc.ncbi.nlm.nih.gov/articles/PMC11742719/) |
| **Đơn vị** | Vellore Institute of Technology + NIT Rourkela (Ấn Độ) |

**Phần cứng (chi tiết, từ full text):**
- **Raspberry Pi 4 Model B** — edge device quản lý **4 camera** (USB + cổng Pi camera)
- **ESP32 (ESP-WROOM-32)** — **một con mỗi ô đỗ**, kèm pin riêng
- Cảm biến IR: ngoài trời gắn dưới đất "giữa hai bánh xe"; trong nhà gắn tường
- Camera: yêu cầu tối thiểu **1080p, auto-focus, HDR**
- **Smart Metering Display (SMD)** ở cổng ra hiển thị phí

**Stack phần mềm:** YOLO (không nêu version) + **Tesseract OCR** + tiền xử lý OpenCV (Gaussian blur → threshold → Canny → HSV/grayscale) + **SQL Server (SSMS) / SQLite**

**Kiến trúc 3 module:** VRS (camera vào/ra ghi biển + timestamp) · VPDS (IR + ESP32 + camera mỗi ô, **tọa độ ô liên kết với cảm biến để dual verification**) · SMD (đo thời lượng + hiển thị phí)

**Logic tính phí:** `Phí = Thời lượng đỗ × Chi phí mỗi giây`, có **dynamic pricing theo giờ cao/thấp điểm**

**Số liệu + protocol đo (quan trọng — có ghi rõ điều kiện):**

| Metric | Giá trị | Điều kiện đo |
|---|---|---|
| Nhận dạng biển số | **95%** | Ban ngày |
| Nhận dạng biển số | **90%** | Ánh sáng yếu |
| Nhận dạng biển số | **93%** | Góc 45° |
| Detect xe | **88%** | Khoảng cách 1.5–3 m |
| **Khớp biển số tổng thể** | **88.9%** | **trên 100 test case** |
| Sai số theo dõi occupancy | **< 5%** | so với đếm thủ công |
| Giảm lỗi tính tiền | **90%** | so với phương pháp cũ |

Điều kiện test gồm: ánh sáng ban ngày/yếu/nhân tạo, góc 0° và 45°, khoảng cách 1.5–3 m, hai hướng sáng (ngược/xuôi nắng).

**Hạn chế (paper tự nêu):** accuracy dao động theo ánh sáng; góc 45° làm giảm còn 93%; "một vài test case fail" **không phân tích nguyên nhân gốc**. Không tách bạch accuracy cấp biển vs cấp ký tự.

**Code/dataset:** ❌ Không public. Dataset "available from the corresponding author upon reasonable request".

**So với hệ thống mình — đối chiếu trực tiếp:**

| Khía cạnh | Pradhan 2025 | Hệ thống mình |
|---|---|---|
| Edge | Pi 4B + ESP32/ô | **Pi 5, không cần ESP32** (occupancy suy từ session) |
| OCR | Tesseract (cũ, yếu với biển VN) | **PaddleOCR/EasyOCR** → kỳ vọng vượt 88.9% |
| Occupancy | Cảm biến IR mỗi ô (tốn phần cứng) | Suy từ session vào/ra (rẻ hơn, ít phần cứng) |
| Chống gian lận | Dual verification IR + tọa độ | **Biển số + màu biển** (không hệ nào có) |
| DB | SQL Server/SQLite | PostgreSQL |

**→ 88.9% là con số baseline system-level so sánh trực tiếp nhất của đồ án.** **BibTeX:** `pradhan2025iotparking`

---

#### A2.2 · Ammar và cộng sự 2023 — nhận dạng xe + biển số đa tầng, edge tại cổng bãi xe ✅ **FULL**

> **Analogue học thuật gần nhất cho use-case access-control chạy trên edge. Đoạt 2 giải thưởng (2021, 2022).**

| Mục | Nội dung |
|---|---|
| **Trích dẫn** | A. Ammar, A. Koubaa, W. Boulila, B. Benjdira, and Y. Alhabashi, "A Multi-Stage Deep-Learning-Based Vehicle and License Plate Recognition System with Real-Time Edge Inference," *Sensors*, vol. 23, no. 4, p. 2120, 2023. |
| **DOI / link** | [10.3390/s23042120](https://doi.org/10.3390/s23042120) · **full text mở:** [PMC9966104](https://pmc.ncbi.nlm.nih.gov/articles/PMC9966104/) |
| **Nơi triển khai** | **Cổng bãi xe nhân viên + cổng chính** campus Prince Sultan University, Riyadh |

**Pipeline 5 tầng (có input size cụ thể):**
1. **YOLOv4** (416×416) detect xe + biển số — nguồn video **RTSP stream**
2. **Xception** (pretrain ImageNet) + avg-pool 4×4 + 3 FC layer → phân loại **196 lớp đời xe**
3. Nhận dạng ký tự — 2 phương án: *Model 1* YOLOv3 (320×320) + MobileNetV2 CNN (54 lớp ký tự); ***Model 2b (được chọn)*** YOLOv4 (416×416) → **27 lớp ký tự đôi**
4. **DeepSORT tùy biến** + cơ chế **voting qua nhiều frame**
5. Tối ưu bằng **NVIDIA TensorRT** (quantization + layer/tensor fusion)

**Dataset (tất cả tự thu, biển Saudi):**

| Thành phần | Cỡ |
|---|---|
| Detect xe + biển | 203 ảnh / 819 xe / 246 biển |
| Phân loại đời xe | 41.521 ảnh, 196 lớp |
| Detect ký tự đơn | 373 ảnh biển crop, 5.193 ký tự |
| Phân loại ký tự | 18.422 ảnh ký tự |
| Detect ký tự đôi | 593 ảnh, 3.827 ký tự đôi |
| **Đánh giá** | **2 video (11m18s + 21m28s) + 100 ảnh tĩnh** |

**Số liệu + protocol (IoU 0.5):**

| Metric | Giá trị |
|---|---|
| mAP detect (tổng) | **74.1%** — AP xe 67.6%, AP biển 80.7% |
| Phân loại đời xe | precision 97.5%, recall/F1/accuracy 97.3% |
| Detect ký tự đơn / đôi (val) | mAP 99.8% / 99.0% |
| **Ảnh tĩnh** (Model 2b) | ký tự đúng 92.5%, **biển đầy đủ đúng 53%**, 9.5 FPS |
| **Video 1** | ký tự 81.9%, biển đầy đủ **67%**, 14.4 FPS |
| **Video 2** | ký tự 95%, biển đầy đủ **80%**, 18.4 FPS |
| **Tổng hợp** | ký tự **88.6%**, biển đầy đủ **74%**, **17.1 FPS** trên Jetson Xavier AGX |

**Ba phát hiện có thể áp dụng trực tiếp cho đồ án:**

1. **Voting theo frame là cú tăng accuracy rẻ nhất:** "accuracy jumps from **29% when using a single frame to 69% when using a maximum of 35 frames**". Xử lý video thay vì ảnh tĩnh tăng **tương đối 40%** cho biển số. → Camera cổng của mình nên đọc nhiều frame rồi vote, không đọc 1 frame.
2. **Độ phân giải camera quyết định:** cùng Video 2 —

   | Độ phân giải | Miss biển | Ký tự đúng | Biển đúng | FPS |
   |---|---|---|---|---|
   | 1920×1080 | 0% | 95% | **80%** | 18.4 |
   | 1280×720 | 2% | 91.2% | 72% | 19.5 |
   | 720×480 | 20% | 79.3% | **23%** | 21.2 |

   → **Xuống 480p làm sập accuracy từ 80% còn 23%.** Chốt spec camera ≥ 720p, ưu tiên 1080p cho hệ thống mình.
3. **Khoảng cách val-vs-thực tế:** ký tự val 99.8% nhưng biển đầy đủ thực tế 74% → đúng bài học phải báo cáo cả hai cấp.

**Hạn chế (paper tự nêu):** "significant gap between the accuracy achieved on validation datasets in a constrained environment and the accuracy obtained in realistic unconstrained environments"; 14% xe có đời không nằm trong tập train. **Future work của họ nêu đúng vấn đề của mình: "securing the identity and the privacy of license plates" và "protecting the ANPR system from forgery"** → hỗ trợ phần tuân thủ luật dữ liệu cá nhân + chống gian lận của đồ án.

**Code:** ❌ Không public; data "not publicly available due to privacy issues". **BibTeX:** `ammar2023multistage`

---

#### A2.3 · Al-batat và cộng sự 2022 — ALPR end-to-end, **có code mở** ✅ **FULL**

> **Giá trị lớn nhất: là paper duy nhất trong khảo sát vừa có full text mở, vừa có code chạy được, vừa đánh giá trên 5 dataset công khai.**

| Mục | Nội dung |
|---|---|
| **Trích dẫn** | R. Al-batat, A. Angelopoulou, S. Premkumar, J. Hemanth, and E. Kapetanios, "An End-to-End Automated License Plate Recognition System Using YOLO Based Vehicle and License Plate Detection with Vehicle Classification," *Sensors*, vol. 22, no. 23, p. 9477, 2022. |
| **DOI / link** | [10.3390/s22239477](https://doi.org/10.3390/s22239477) · **full text mở:** [PMC9737602](https://pmc.ncbi.nlm.nih.gov/articles/PMC9737602/) |
| **🔑 CODE MỞ** | **[github.com/RedaAlb/alpr-pipeline](https://github.com/RedaAlb/alpr-pipeline)** — MIT licence, Darknet framework (verify GitHub API 2026-07-21: 9★/3 fork) |

**Pipeline (có input size):** YOLOv2 (608×416) detect xe → YOLOv4-tiny (416×416) detect biển → YOLOv4-tiny (**352×128**, chọn theo "average aspect ratio (w/h) of all LP patches across all datasets is 2.86") nhận dạng ký tự → ResNet50 phân loại loại xe

**Dataset — 5 tập công khai, 7.290 mẫu, đa vùng:**

| Dataset | Vùng | Mẫu | Độ phân giải |
|---|---|---|---|
| Caltech Cars | Mỹ | 124 | 896×592 |
| English LP | EU | 509 | 640×480 |
| OpenALPR EU | EU | 108 | đa dạng |
| AOLP | Đài Loan | 2.049 | đa dạng |
| UFPR-ALPR | Brazil | 4.500 | 1920×1080 |

**Protocol đo (rất rõ ràng — mẫu tốt để mình bắt chước):** 36 lớp ký tự (0-9, A-Z); Precision = TP/(TP+FP), Recall = TP/(TP+FN); **IoU riêng cho từng tầng: VD 0.25, LPD 0.65, LPR 0.5**; kết quả **trung bình qua 5 lần chia train/val/test ngẫu nhiên (0.7/0.2/0.1)**.

**Số liệu theo tầng:**

| Tầng | Precision | Recall |
|---|---|---|
| Detect xe (VD) | 99.71% | 99.90% |
| Detect biển (LPD) | 99.16% | 99.36% |
| Nhận dạng (LPR, tách riêng) | **99.68%** | 97.69% |
| **Toàn pipeline** | **90.3%** accuracy TB (cấp ký tự, qua cả 5 dataset) | |
| Phân loại loại xe (ResNet50) | **98.22%** (3 lớp: xe khẩn cấp 449 / xe tải 374 / khác 831) | |

**Tốc độ (GTX 1060 — GPU đời thấp):** 1 xe **18 FPS**, 2 xe 13 FPS, 3 xe 11 FPS. Tác giả tự lưu ý kết quả "are not a fair comparison to other methods because a very low-end GPU was used".

**Hạn chế + failure case (rất hữu ích):**
- **Ký tự khó nhất: "O" chỉ 38.96% AP**, "K" 83.86%, "M" 86.50%, "Q" 70.84% → nhóm ký tự dễ nhầm
- UFPR-ALPR chỉ **62.06%** theo frame, lên 73.33% nếu dùng consensus 3 frame (**lại củng cố ý tưởng voting đa frame**)
- Test set nhỏ ở vài dataset gây "huge impact on the final recall"
- Cố ý **không dùng post-processing rule** → khác mình (mình dùng regex định dạng biển VN)

**So với hệ thống mình:** ⭐ **Đây là repo engineering nên đọc đầu tiên** — cùng cấu trúc cascade, code MIT chạy được, protocol đo rõ ràng để mình sao chép cách trình bày trong chương evaluation. Ký tự "O" 38.96% cảnh báo trực tiếp: **biển VN cũng có cặp O/0, B/8, D/0 dễ nhầm** → cần dựng confusion matrix cấp ký tự ở tuần 9. **BibTeX:** `albatat2022endtoend` + code `redalb2022alprcode`

---

#### A2.4 · Safran và cộng sự 2024 — YOLOv8 đa tầng **kèm web dashboard** ⚠️ **ABSTRACT**

> **Sửa từ pass 1: paper này CÓ web dashboard — trước đó feature matrix của mình ghi thiếu.**

| Mục | Nội dung |
|---|---|
| **Trích dẫn** | M. Safran, A. Alajmi, and S. Alfarhood, "Efficient Multistage License Plate Detection and Recognition Using YOLOv8 and CNN for Smart Parking Systems," *Journal of Sensors*, vol. 2024, art. 4917097, pp. 1–18, 2024. |
| **DOI / link** | [10.1155/2024/4917097](https://doi.org/10.1155/2024/4917097) |
| **Tác giả (verified)** | Mejdl Safran; Abdulmalik Alajmi; Sultan Alfarhood — Crossref 2026-07-21 (pass 1 ghi "và cộng sự", nay đủ) |
| **Kiến trúc** | **YOLOv5** detect biển → **YOLOv8** detect ký tự → **CNN mới** phân loại ký tự |
| **Dataset** | Tự thu, biển số **Saudi**; dùng **camera giám sát có sẵn trong bãi** (không lắp thêm phần cứng) |
| **Số liệu** | Đa tầng **96.1%** vs single-stage **83.9%**; nhận dạng ký tự CNN 97% |
| **🔑 Dashboard** | *"integrated into a **web-based dashboard** for real-time visualization and statistical analysis of car park occupancy and vehicle movement with an acceptable time efficiency"* |

**Hai luận điểm dùng được ngay trong Tổng quan:**
1. **Bằng chứng định lượng cho kiến trúc theo tầng:** 96.1% vs 83.9% → đúng lý do mình tách detect biển rồi mới đọc, thay vì detect ký tự một lần.
2. **Luận điểm chống cảm biến:** abstract nêu thẳng hệ thống dùng cảm biến "entail high installation and maintenance costs and limited functionality in tracking vehicle movement" → **trích câu này để biện minh hướng vision-only của đồ án.**

**So với hệ thống mình:** cặp gần nhất về mặt sản phẩm (ALPR đa tầng + dashboard thống kê occupancy). Khác biệt còn lại của mình: edge deployment + màu biển + biển VN 2 hàng. **BibTeX:** `safran2024multistage`

---

#### A2.5 · Rani và cộng sự 2024 — IPS: module vào/ra + thanh toán QR ⚠️ **ABSTRACT**

| Mục | Nội dung |
|---|---|
| **Trích dẫn** | R. Rani, S. Kumar, S. K. Pippal, M. Gund, U. Chaudhari, R. Agrawal, M. Dalsaniya, and L. Verma, "IPS: Intelligent Parking System Using YOLO and Image Processing," *Int. J. Transport Development and Integration*, vol. 8, no. 3, pp. 447–453, 2024. |
| **DOI / link** | [10.18280/ijtdi.080308](https://doi.org/10.18280/ijtdi.080308) · [Acadlore](https://www.acadlore.com/article/IJTDI/2024_8_3/ijtdi.080308) |
| **Kiến trúc** | **YOLOv5m** detect biển + OCR; module vào ghi biển + timestamp, tài xế chọn block; module ra tính phí theo thời lượng và sinh **QR code động thanh toán không tiếp xúc** |
| **Dataset** | 3.500 ảnh, chia 70/30 |
| **Số liệu** | LPR **97.11%** (không tính khoảng trắng) / **91.91%** (tính cả khoảng trắng); recall 97.25% |

**Chi tiết đáng chú ý:** chênh lệch **97.11% vs 91.91% chỉ do cách xử lý khoảng trắng** → minh chứng "accuracy" phụ thuộc định nghĩa đến mức nào. **Chương evaluation của mình phải nêu rõ quy tắc chuẩn hoá chuỗi biển số** (bỏ khoảng trắng/gạch ngang hay không) trước khi công bố số.

**So với hệ thống mình:** vòng vào/ra + phí giống hệt business logic module FastAPI. **QR động lúc ra là feature mở rộng ứng viên** cho dashboard tuần 5. **BibTeX:** `rani2024ips`

---

#### A2.6 · Arukonda và cộng sự 2026 — YOLOv8 + OCR phân bổ chỗ đỗ ⚠️ **ABSTRACT**

| Mục | Nội dung |
|---|---|
| **Trích dẫn** | S. Arukonda, G. S. Jayanth, A. S. S. Koushik, T. Sarupya, P. V. Kumar, and K. B. Reddy, "Real-Time Vehicle Number Plate Recognition and Smart Parking Allocation Using YOLOv8 and OCR for Intelligent Urban Mobility," *Int. J. Intelligent Transportation Systems Research*, 2026. |
| **DOI / link** | [10.1007/s13177-025-00612-7](https://doi.org/10.1007/s13177-025-00612-7) |
| **Tác giả (verified)** | 6 tác giả đầy đủ qua Crossref 2026-07-21 (pass 1 chỉ có 3 + "et al.") |
| **Kiến trúc** | YOLOv8 detect biển trên video trực tiếp → EasyOCR + Tesseract → hậu xử lý sửa ký tự + **validate định dạng theo quốc gia** → phân bổ chỗ theo rule (20 chỗ, cánh Đông/Tây) → ghi log **Excel** |
| **Dataset** | Tự gán nhãn, 5.000+ ảnh |
| **Số liệu** | Detect **98.5%**, precision 98.2%, recall 97.8%, F1 98.0%; **latency 50 ms/frame** |
| **⚠️ Lỗ hổng** | **Không nêu phần cứng** cho con số 50 ms → không so sánh được với Pi 5. Chỉ dùng làm mốc accuracy, **không dùng làm mốc latency.** |

**So với hệ thống mình:** bước **validate định dạng theo quốc gia** tương ứng trực tiếp với regex biển VN của mình. Việc họ dùng **Excel làm backend** cho thấy khoảng trống mà PostgreSQL + FastAPI của mình lấp — nêu được trong Tổng quan như điểm mạnh kỹ thuật. **BibTeX:** `arukonda2026smartparking`

---

#### A2.7 · Moussaoui và cộng sự 2024 — YOLOv8 + EasyOCR ⚠️ **ABSTRACT** (Crossref đầy đủ)

| Mục | Nội dung |
|---|---|
| **Trích dẫn** | H. Moussaoui, N. El Akkad, M. Benslimane, W. El-Shafai, A. Baihan, C. Hewage, and R. S. Rathore, "Enhancing automated vehicle identification by integrating YOLO v8 and OCR techniques...," *Scientific Reports*, vol. 14, art. 14389, 2024. |
| **DOI / link** | [10.1038/s41598-024-65272-1](https://doi.org/10.1038/s41598-024-65272-1) |
| **Pipeline (từ abstract)** | Thu **270 ảnh từ internet** → gán nhãn bằng **CVAT** → YOLOv8 detect vùng biển → **k-means clustering + thresholding + phép mở (opening) morphology** làm rõ ký tự → OCR → sinh file text kèm mã quốc gia |
| **Số liệu** | Detect/precision/recall **99%**, nhận dạng ký tự **98%**; metric dùng: precision, recall, F1, **CLA** |
| **🚩 Cảnh báo** | **Chỉ 270 ảnh** — con số 99% gần như chắc chắn bị thổi phồng do test set nhỏ. Không có latency/FPS. |

**So với hệ thống mình:** (a) xác nhận cặp YOLOv8+EasyOCR mình định dùng là khả thi; (b) **chuỗi tiền xử lý k-means + threshold + opening là tham khảo tốt cho module xử lý ảnh biển của Đức**; (c) là **ví dụ phản diện** cho chương evaluation — mình phải ghi cỡ test set cạnh mọi con số accuracy. **BibTeX:** `moussaoui2024yolov8ocr`

---

### A3. ALPR trên edge — bằng chứng lượng hoá cho INT8

---

#### A3.1 · Sonnara và cộng sự 2025 — "Light-Edge" INT8 trên Jetson Nano ✅ **FULL** (CC-BY, đã tải PDF)

> **Nguồn định lượng tốt nhất cho câu hỏi "INT8 mất bao nhiêu accuracy, được bao nhiêu tốc độ" — chính là thí nghiệm tuần 7 của mình.**

| Mục | Nội dung |
|---|---|
| **Trích dẫn** | F. Sonnara, H. Chihaoui, and F. Filali, "Efficient real-time license plate recognition using deep learning on edge devices," *J. Real-Time Image Processing*, vol. 22, no. 5, art. 159, 2025. |
| **DOI / link** | [10.1007/s11554-025-01738-3](https://doi.org/10.1007/s11554-025-01738-3) — **CC-BY 4.0, PDF mở** |
| **Kiến trúc** | **Light-Edge**: backbone **ResNet-18 + FPN dùng chung**, head detect **anchor-free**, head nhận dạng **CTC** — một network vừa detect vừa đọc. Khối **1×1 channel-fusion** loại bỏ **28% số convolution**. |
| **Ràng buộc thiết kế** | Phần cứng roadside **< 10 W**, RAM hạn chế, kết nối chập chờn → loại bỏ phương án offload lên cloud |

**Dataset — CCPD (Chinese City Parking Dataset), mô tả rất kỹ:**
- Tổng **290.316 ảnh** 720×1280, camera cố định ở Bắc Kinh (2016–2018); tên file mã hoá sẵn 4 góc biển + chuỗi 7 ký tự (không cần file annotation riêng)
- Official split: **200.000 train / 20.000 val / 20.000 test**, cộng 6 subset đánh giá (Blur, FN, Rotate, Tilt, Weather, Challenge = **50.316 ảnh**)
- ⚠️ **Nhóm này chỉ train trên 30.000 ảnh + 2.000 val** (do trần RAM 4 GB của Jetson Nano) nhưng **luôn đánh giá trên đủ 20.000 ảnh test**
- Đa dạng: **61.4% ngày / 38.6% đêm**; quay trong mặt phẳng ±60°, nghiêng ngoài mặt phẳng tới 45°; bề rộng biển 40–420 px (TB 138 px)

**Training:** Adam, **38 epoch**, batch 32, α=0.9 (ưu tiên loss nhận dạng), lr 1e-3 chia 10 mỗi 10 epoch, dừng khi val loss không cải thiện 3 epoch liên tiếp.

**🔑 Bảng 2 — kết quả trên Jetson Nano (export ONNX → TensorRT 8.5, input 1×1280×720):**

| Phương pháp | Model (MB) | FPS ↑ | mAP (%) ↑ | Điện (W) ↓ |
|---|---|---|---|---|
| TE2E | 145 | 2.1 | 88.4 | 9.5 |
| RPNet | 92 | 11.3 | 90.0 | 10.1 |
| AF-Net | 56 | 8.1 | **97.2** | 8.8 |
| YOLOv8-MobileLPR (re-impl.) | 68 | 9.5 | 89.8 | 9.3 |
| **Light-Edge (FP32, trước tối ưu)** | 38 | **3.1** | **90.6** | 5.4 |
| **Light-Edge (TensorRT INT8)** | 38 | **14.2** | **90.2** | 4.8 |

**Kết luận về INT8 (nguyên văn):** *"INT8 quantisation and kernel fusion raise throughput from 3.1 fps to 14.2 fps yet cost only **−0.4 pp mAP**"* → **tăng tốc 4.6×, chỉ mất 0.4 điểm mAP.**

**⚠️ Nuance then chốt cho tuần 7 (chỉ có trong full text, không có trong abstract):** paper giải thích vì sao mất ít accuracy đến vậy — *"TensorRT leaves the **first and last layers in FP16**, preserving representational fidelity where it matters most"*. **Đây KHÔNG phải INT8 thuần mà là quantization hỗn hợp** (abstract gọi là "mixed-precision"). → Khi lượng tử hoá trên Pi 5, mình nên **giữ layer đầu/cuối ở độ chính xác cao** thay vì INT8 toàn bộ; đây là kỹ thuật cụ thể, có bằng chứng, để áp dụng.

**Ablation (Bảng 3):** bỏ khối 1×1 fusion → mAP 90.2% → 88.4% (−1.8 pp), FPS 14.2 → 11.6.

**🚩 Mâu thuẫn nội tại trong paper (phát hiện khi đọc full text):** throughput-per-watt được ghi ba lần khác nhau — "tripling" (§1), "0.57 → 2.96 fps·W⁻¹" (= 5.2×, §3), và "improves 13×" (§5). **Đừng trích con số throughput-per-watt của paper này**; các số FPS/mAP/W trong Bảng 2 thì nhất quán và dùng được.

**So với hệ thống mình:** đây là **hình mẫu trực tiếp cho thí nghiệm tuần 7** — báo cáo FP32 vs INT8 trên cùng một bảng gồm model size, FPS, mAP, điện năng. Lưu ý AF-Net đạt mAP cao hơn (97.2%) nhưng chậm và tốn điện gấp đôi → minh hoạ đúng đánh đổi accuracy-vs-edge mà đồ án mình phải lập luận. **BibTeX:** `sonnara2025lightedge`

---

#### A3.2 · Zhu và cộng sự 2025 — YOLOv8n cải tiến cho biển số nhỏ ⚠️ **ABSTRACT** (Crossref đầy đủ)

| Mục | Nội dung |
|---|---|
| **Trích dẫn** | R. Zhu, Q. He, H. Jin, Y. Han, and K. Jiang, "License Plate Detection Based on Improved YOLOv8n Network," *Electronics*, vol. 14, no. 10, p. 2065, 2025. |
| **DOI / link** | [10.3390/electronics14102065](https://www.mdpi.com/2079-9292/14/10/2065) |
| **Cải tiến** | Thiết kế lại **C2f**, **SPPF**, và **detection head**; thay **CIoU → WIoU** loss |
| **Dataset** | Tự thu, cảnh giám sát, đa dạng ánh sáng/nền/góc/loại xe |
| **Số liệu** | mAP@0.5 **90.9% → 94.4%**; precision 90.2% → 92.8%; recall 82.9% → 87.9%; **tham số giảm 3.1M → 2.1M**; **86 FPS** |

**So với hệ thống mình:** ⭐ **Hướng future-work cụ thể nhất nếu recall biển số của mình yếu** — họ vừa **tăng** mAP vừa **giảm** 32% tham số (3.1M → 2.1M), tức mô hình nhẹ hơn cho Pi 5 chứ không nặng thêm. Đúng bài toán của mình: biển nhỏ, xiên, nền phức tạp. **BibTeX:** `zhu2025licenseplate`

---

### A4. Bãi xe dựa trên cảm biến IoT — đối chứng với hướng vision

- **Ndunda & Nicolas 2026** — E. Ndunda and A. Nicolas, "Smart On-Street Parking: Survey of Actual Implementations in Cities and Insights from Practitioners," [arXiv:2602.06517](https://arxiv.org/abs/2602.06517), 2026. Khảo sát ~25 deployment thực tế + phỏng vấn practitioner tại 10 thành phố. Phát hiện: cảm biến từ chôn dưới đất đầu thập niên 2010 **hỏng phần cứng** khiến dự án chết yểu; xu hướng dịch sang **camera tĩnh** (nhiều chỗ đỗ/thiết bị) và camera ALPR tuần tra. → **Luận điểm chống cảm biến cho Tổng quan.** BibTeX: `ndunda2026onstreet`
- **Safran 2024** (A2.4) độc lập xác nhận: cảm biến "entail high installation and maintenance costs and limited functionality in tracking vehicle movement".
- **Pradhan 2025** (A2.1) là phản ví dụ hybrid: IR mỗi ô *cộng* ALPR — đổi lấy sai số occupancy < 5% bằng chi phí một ESP32+IR mỗi ô.
- Tham khảo ngành (phi học thuật): cảm biến siêu âm mỗi ô quảng cáo ~97% trong nhà nhưng cần lắp overhead có nguồn mỗi chỗ; camera phủ nhiều chỗ và đồng thời làm occupancy + biển số + dwell time ([Parking BOXX](https://parkingboxx.com/blog/technology/parking-occupancy-sensors-explained/)).

**Tổng hợp lập luận cho Tổng quan:** ba nguồn độc lập (khảo sát thực địa Ndunda, paper Safran, chi phí phần cứng Pradhan) cùng chỉ ra cảm biến mỗi ô đắt và khó bảo trì → **camera-based là lựa chọn có căn cứ, không phải mặc định.**

---

## B. Sản phẩm thương mại

### B1. Vendor Việt Nam

| Sản phẩm | Claim ALPR | Edge | Dashboard / tính năng | Giá (2026-07-19) |
|---|---|---|---|---|
| **VETC** | RFID eTag + camera AI ANPR đối chiếu chéo; server khớp identity RFID với biển camera đọc ([VETC FAQ](https://vetc.com.vn/hoi-dap-ve-giai-phap-gui-xe-thanh-toan-dien-tu-khong-dung-vetc-n365.html)) | Thiết bị lane tại chỗ | Thanh toán không dừng từ tài khoản VETC; **đối chiếu RFID↔ANPR loại bỏ gian lận đổi vé** ([eParking](https://eparking.vn/etc-bai-xe/)) | B2B |
| **ePass / Giao thông số** (Viettel) | Claim **99.95%** — ⚠️ đây là **accuracy đọc thẻ RFID, KHÔNG phải camera ALPR** ([Brixton](https://brixtonvietnam.com.vn/tim-hieu-ve-the-thu-phi-khong-dung-vetc-va-epass)) | Hạ tầng lane | Trừ phí từ tài khoản ePass ([giaothongso.com.vn](https://giaothongso.com.vn/thu-phi-bai-do-xe-khong-su-dung-tien-mat-bang-tai-khoan-epass/)) | B2B |
| **PTH MParking** | "Nhận diện biển số siêu tốc" trên smartphone, không công bố % ([sản phẩm](https://hethonggiuxethongminhpth.com/san-pham/phan-mem-giu-xe-tren-dien-thoai)) | "Zero-hardware": điện thoại Android làm thiết bị cổng (NFC + chụp biển) | Quản lý doanh thu, ảnh vào/ra real-time, claim "chống thất thoát 100%" | Từ **300.000 VNĐ/tháng** |
| MegaParking, VietParking, TB-iParking, SDT Parking | Lane quẹt thẻ + ANPR cho hầm chung cư/văn phòng; không công bố accuracy ([MegaParking](https://megaparking.vn/phan-mem-quan-ly-he-thong-bai-giu-xe-thong-minh/), [VietParking](https://baigiuxethongminh.vn/), [TB-iParking](https://tbvision.com.vn/phan-mem-quan-ly-bai-giu-xe-thong-minh-tb-iparking)) | PC lane + camera IP | Ảnh vào/ra, báo cáo phí, vé tháng | Theo dự án |

### B2. Vendor quốc tế

| Sản phẩm | Claim ALPR | Edge | Dashboard | Giá |
|---|---|---|---|---|
| **Plate Recognizer** + **ParkPow** | Không công bố accuracy %; "works with blurry, low-res, night-time photos"; 90+ quốc gia. **SDK 50–100 ms**, cloud ~200 ms ([site](https://platerecognizer.com/)) | **SDK on-prem chạy Jetson, Raspberry Pi**, Windows/Linux | Log vào/ra + duration, báo cáo occupancy, thực thi policy (giới hạn 3h), tìm theo biển/hãng/model/màu, custom tag + 6 field, alert email/Slack/Teams/SMS, AI xác định hướng xe vào-vs-ra, export CSV/API ([ParkPow](https://platerecognizer.com/parkpow/), [features](https://parkpow.com/features/), [alerts](https://guides.platerecognizer.com/docs/parkpow/user-guide/settings/alerts/)) | Free 2.500 lookup/th; $50/th cho 50k; Stream $35–45/camera/th ([pricing](https://platerecognizer.com/pricing/)) |
| **Rekor Scout / OpenALPR** | "Best-in-class" (không có %); biển + hãng/model/màu/hướng, ~70 quốc gia ([Scout](https://www.openalpr.com/software/scout)) | Agent trên phần cứng thường; camera **Edge Pro** $1.250 ([Edge Pro](https://www.rekor.ai/systems/edge-pro)) | Dashboard web, alert list, lưu 60 ngày (Pro) | $5/th home; Basic **$12/th/camera** ([docs](https://docs.rekor.ai/scout/getting-started/subscriptions-and-licensing)) |
| **Survision** | Không công bố %; thay bằng **Performance Warranty** hợp đồng (tỷ lệ đọc tối thiểu hoặc hoàn tiền); "in as little as 20 ms"; tới 250 km/h ([accuracy](https://survisiongroup.com/post-lets-be-accurate-about-lpr-accuracy), [gen 5](https://survisiongroup.com/post-introducing-the-5th-generation-of-survision-cameras)) | Camera LPR all-in-one xử lý nhúng ([Nanopak](https://survisiongroup.com/post-nanopak)) | Vendor phần cứng, tích hợp vào PARCS | Bán phần cứng |

**Ba bài học cho đồ án:**
1. **Không vendor nghiêm túc nào công bố một con số accuracy trần trụi.** Survision lập luận thẳng rằng claim accuracy một con số là ill-posed và bán warranty thay thế → **chương evaluation của mình nên báo cáo accuracy *theo điều kiện* (ngày/đêm/góc), đúng cách Pradhan 2025 làm**, thay vì một con số duy nhất.
2. **Chuẩn thị trường VN là RFID/thẻ + ANPR đối chiếu chéo** để chống gian lận. Hệ thống pure-vision của mình phải **thừa nhận đây là hạn chế** và trình bày cách bù: ảnh vào + biển số + **màu biển** = kiểm tra ba lớp.
3. **ParkPow là tài liệu tham khảo dashboard phong phú nhất** (tag, alert overstay/ngoài giờ, drill-down search, export CSV) — bám sát danh sách này cho tuần 5.

---

## C. Dự án mã nguồn mở

> **Toàn bộ số sao / license / ngày push cuối verify qua GitHub REST API ngày 2026-07-21** (pass 1 lấy ước lượng từ trang web, nay là số chính xác).

### C1. Repo Việt Nam

| Repo | Stack | ★ / fork | License | Push cuối | Đánh giá |
|---|---|---|---|---|---|
| [winter2897/Real-time-Auto-LPR-Jetson-Nano](https://github.com/winter2897/Real-time-Auto-License-Plate-Recognition-with-Jetson-Nano) | SSD-MobileNet-v1 detect + SSD OCR (36 class); Colab→ONNX→TensorRT; **claim 40 FPS Jetson Nano** | 226 / 61 | 🚨 **KHÔNG CÓ** | 29/07/2021 | Biển VN + **công bố dataset VN**; nhưng đã 5 năm không cập nhật |
| [trungdinh22/License-Plate-Recognition](https://github.com/trungdinh22/License-Plate-Recognition) | YOLOv5 2 giai đoạn (biển → ký tự); PC webcam 15–20 FPS | 100 / 44 | 🚨 **KHÔNG CÓ** | 13/07/2022 | **Hỗ trợ biển VN 1 hàng + 2 hàng**; dataset từ Mì AI + winter2897 |
| [mrzaizai2k/VIETNAMESE_LICENSE_PLATE](https://github.com/mrzaizai2k/VIETNAMESE_LICENSE_PLATE) *(mới, pass 2)* | KNN + OpenCV (không deep learning); **biển VN 1 và 2 hàng**; **use-case bãi giữ xe** | 36 / 21 | ✅ **MIT** | 14/11/2025 | Duy nhất trong nhóm VN: có license rõ + còn bảo trì |

**🚨 Cảnh báo pháp lý cho đồ án:** hai repo VN phổ biến nhất (winter2897, trungdinh22) **không khai báo license** → theo mặc định luật bản quyền, **không được phép tái sử dụng code trong đồ án**. Dataset họ công bố có thể dùng nếu ghi nguồn, nhưng **code thì không**. Nếu cần tham khảo code có license hợp lệ → dùng `mrzaizai2k` (MIT) hoặc `fast-alpr` (MIT).

### C2. Repo quốc tế

| Repo | Stack | ★ / fork | License | Push cuối | Đánh giá |
|---|---|---|---|---|---|
| [ankandrew/fast-alpr](https://github.com/ankandrew/fast-alpr) | YOLOv9-t detect + CCT OCR (`fast-plate-ocr`), **ONNX Runtime** (CPU/CUDA/OpenVINO/DirectML/QNN) | **724** / 119 | ✅ MIT | **16/03/2026** | ⭐ ALPR OSS hiện đại tốt nhất, **còn bảo trì tích cực**; path ONNX CPU hợp ARM; tham khảo chính cho đóng gói ONNX của mình |
| [RedaAlb/alpr-pipeline](https://github.com/RedaAlb/alpr-pipeline) *(mới, pass 2)* | YOLO Darknet + ResNet phân loại xe — **code chính thức của paper Al-batat 2022 (A2.3)** | 9 / 3 | ✅ MIT | 31/05/2023 | ⭐ Hiếm: paper + code + protocol đo khớp nhau |
| [zxllxz2/smart-parking-system](https://github.com/zxllxz2/smart-parking-system) | Frontend **React** Material Dashboard 2; xem slot, park/checkout, thanh toán | 3 / 3 | ✅ MIT | 19/02/2023 | Chỉ tham khảo **layout dashboard React** (không có ALPR) |
| [pratik2374/Automated-Car-parking-system](https://github.com/pratik2374/Automated-Car-parking-system) | Flask + YOLO + Tesseract + ThingSpeak | 1 / 2 | ✗ | 21/03/2026 | Giá trị thấp |
| [playatanu/smart-car-parking](https://github.com/playatanu/smart-car-parking) | YOLO + OCR, tracking, timestamp vào/ra | 0 / 0 | ✗ | 13/02/2025 | Chỉ ý tưởng session-logging |

**Nhận xét định vị (quan trọng cho Tổng quan):** không dự án OSS nào kết hợp **ALPR edge + backend thật (DB, session, phí) + dashboard web**. Chúng hoặc là thư viện ALPR thuần (fast-alpr, winter2897), hoặc app bãi xe kiểu demo không có ALPR (zxllxz2). **Sự kết hợp đó chính là đóng góp kỹ thuật của đồ án mình** — nêu rõ trong Tổng quan.

---

## D. Bảng so sánh tính năng tổng hợp

Chú thích: ✓ có · ~ một phần · — không có/chưa rõ. Hệ thống VN liệt kê trước; hàng cuối = hệ thống mình.

| Hệ thống | Occupancy real-time | Log session + ảnh | Tính phí | Báo cáo/thống kê | Alert / chống gian lận | Đa camera | Edge / cloud | **Màu biển số** |
|---|---|---|---|---|---|---|---|---|
| VETC/ePass (VN, B) | — | ✓ | ✓ (trừ tài khoản) | ✓ | ✓ (**RFID↔ANPR**) | ✓ | Tại chỗ | — |
| PTH MParking (VN, B) | ~ | ✓ (ảnh vào/ra) | ✓ | ✓ (doanh thu) | ~ ("chống thất thoát") | ~ | Cloud/on-prem | — |
| Tran & Bui 2025 (VN, A1.1) | — | — | — | — | — | — | Edge (Pi 4) | — |
| Dang 2024 (VN, A1.2) | — | — | — | — | — | — | Không nêu | — |
| winter2897 (VN, C1) | — | — | — | — | — | — | Edge (Jetson) | — |
| Pradhan 2025 (A2.1) | ✓ (IR/ô) | ✓ | ✓ (giá động) | ~ | ~ (khớp 88.9%) | ✓ (4 cam) | Edge Pi + server | — |
| Ammar 2023 (A2.2) | — | ~ (log cổng) | — | — | — | ✓ | Edge (Jetson AGX) | — |
| **Safran 2024 (A2.4)** | ✓ | ~ | — | ✓ (**web dashboard**) | — | ✓ (cam có sẵn) | Server | — |
| Rani 2024 (A2.5) | ~ (chọn block) | ✓ | ✓ (**+QR**) | — | — | — | PC | — |
| Arukonda 2026 (A2.6) | ✓ (phân bổ ô) | ~ (Excel) | — | ~ | ~ (validate định dạng) | — | Không nêu | — |
| ParkPow (B2) | ✓ | ✓ (ảnh, duration) | ~ (thiên về policy) | ✓ (drill-down) | ✓ (tag, overstay, ngoài giờ) | ✓ | Cả hai | ~ (màu **xe**) |
| Rekor Scout (B2) | — | ✓ | — | ✓ | ✓ | ✓ | Cả hai | ~ (màu **xe**) |
| fast-alpr (C2) | — | — | — | — | — | — | ONNX di động | — |
| **Hệ thống mình (dự kiến)** | ✓ (suy từ session) | ✓ (PostgreSQL + ảnh vào/ra) | ✓ (rule phí) | ✓ (dashboard React) | ✓ (bất khớp biển+**màu**) | ~ (2 cam cổng) | **Edge (Pi 5, ONNX INT8)** | **✓ (HSV+CLAHE)** |

### Ba điểm khác biệt của đồ án (đã kiểm chứng qua toàn bộ khảo sát)

1. **Phân loại màu biển số làm tín hiệu chống gian lận + phân loại xe** — **cột cuối bảng trên trống hoàn toàn**. Kể cả ParkPow/Rekor cũng chỉ tìm theo *màu xe*, không phải *màu biển*. Vendor VN chống gian lận bằng RFID (phần cứng thêm), không bằng vision. → Đóng góp mới thực sự, không phải claim marketing.
2. **Deploy edge toàn bộ stack trên một Pi 5** (model + FastAPI + DB). Pradhan dùng Pi nhưng vẫn cần server ngoài; Ammar gửi lên cloud; Safran chạy server.
3. **Biển xe máy VN 2 hàng + tuân thủ Luật Bảo vệ dữ liệu cá nhân** (tự xóa sau thời hạn lưu trữ) là yêu cầu hạng nhất — Ammar 2023 nêu privacy là *future work*, mình làm ngay từ thiết kế.

---

## E. Baseline cho chương evaluation (tuần 9)

Nguồn VN đánh dấu **[VN]**. Cột "Evidence" cho biết có thể tin số liệu đến mức nào.

| # | Baseline | Metric | Giá trị | Phần cứng | Evidence | BibTeX |
|---|---|---|---|---|---|---|
| 1 | **[VN]** Tran & Bui 2025 | accuracy nhận dạng | **95.68%** | Raspberry Pi 4B | 🔒 thứ cấp | `tran2025vietnamlpr` |
| 2 | **[VN]** Tran & Bui 2025 | thời gian xử lý | **0.478 s/ảnh** | Raspberry Pi 4B | 🔒 thứ cấp | `tran2025vietnamlpr` |
| 3 | **[VN]** Le 2023 (xe máy) | mAP detect | **93%** | GPU training | 🔒 thứ cấp | `le2023motorcycleplate` |
| 4 | **[VN]** Dang 2024 (bãi trong nhà) | **WER** | **0.014** | không nêu | ⚠️ abstract | `dang2024vietnamcrnn` |
| 5 | **Sonnara 2025** | **INT8 vs FP32** | **3.1 → 14.2 FPS (4.6×), mAP 90.6 → 90.2 (−0.4 pp), 5.4 → 4.8 W** | Jetson Nano | ✅ **bảng gốc** | `sonnara2025lightedge` |
| 6 | Ammar 2023 | FPS edge / biển đầy đủ | **17.1 FPS** / **74%** (video) | Jetson Xavier AGX | ✅ full | `ammar2023multistage` |
| 7 | Ammar 2023 | **hiệu ứng voting đa frame** | **29% (1 frame) → 69% (35 frame)** | — | ✅ full | `ammar2023multistage` |
| 8 | Ammar 2023 | **hiệu ứng độ phân giải** | 1080p **80%** → 720p 72% → 480p **23%** | Jetson AGX | ✅ full | `ammar2023multistage` |
| 9 | Al-batat 2022 | ký tự tách riêng vs toàn pipeline | **99.68%** vs **90.3%** TB | GTX 1060, 18 FPS | ✅ full | `albatat2022endtoend` |
| 10 | Pradhan 2025 | khớp biển số hệ thống | **88.9%** (n=100) | Pi 4B + server | ✅ full | `pradhan2025iotparking` |
| 11 | Pradhan 2025 | accuracy **theo điều kiện** | 95% ngày / 90% tối / 93% góc 45° | Pi 4B | ✅ full | `pradhan2025iotparking` |
| 12 | Safran 2024 | đa tầng vs single-stage | **96.1% vs 83.9%** | camera giám sát | ⚠️ abstract | `safran2024multistage` |
| 13 | Rani 2024 | LPR (ảnh hưởng khoảng trắng) | **97.11%** (bỏ space) / **91.91%** (có space) | PC | ⚠️ abstract | `rani2024ips` |
| 14 | Zhu 2025 | YOLOv8n cải tiến | mAP 90.9 → **94.4%**, tham số 3.1M → **2.1M**, 86 FPS | GPU | ⚠️ abstract | `zhu2025licenseplate` |
| 15 | Arukonda 2026 | accuracy detect | **98.5%** (latency 50 ms ⚠️ **không rõ phần cứng**) | không nêu | ⚠️ abstract | `arukonda2026smartparking` |
| 16 | Moussaoui 2024 | detect / ký tự | 99% / 98% 🚩 **n=270, thổi phồng** | không nêu | ⚠️ abstract | `moussaoui2024yolov8ocr` |
| 17 | **[VN]** winter2897 (OSS) | claim FPS edge | 40 FPS (SSD-MobileNet) | Jetson Nano + TensorRT | claim repo | `winter2897jetsonalpr` |
| 18 | Plate Recognizer (TM) | latency SDK | 50–100 ms/lookup | SDK on-prem | claim vendor | `platerecognizer2026alpr` |

### Cách dùng bảng này trong chương Evaluation

| Mình báo cáo | So với | Lý do |
|---|---|---|
| mAP@0.5 detect biển số | #3 (93%, biển xe máy VN) | Cùng loại biển, cùng nước |
| Accuracy **cấp ký tự VÀ cấp biển số** (tách riêng) | #9 | Bài học Al-batat: chênh 99.68% vs 90.3% |
| Accuracy **chia theo điều kiện** ngày/đêm/góc | #11 | Đúng cách vendor thương mại yêu cầu (mục B) |
| Delta FP32 → INT8 + tăng tốc + điện năng | #5 | Hình mẫu bảng của Sonnara |
| s/xe end-to-end trên Pi 5 | #1, #2 | Baseline VN + Pi gần nhất về phần cứng |
| Tỷ lệ khớp session vào/ra | #10 (88.9%) | Chỉ số system-level duy nhất so sánh được |
| WER (bổ sung) | #4 | Metric của nhóm VN cùng use-case bãi xe |

### Lưu ý protocol **bắt buộc** ghi trong chương

1. **Dataset khác nhau:** CCPD (Trung Quốc), Saudi, Ấn Độ, EU/Mỹ/Brazil/Đài Loan, VN → so sánh **chỉ mang tính tham khảo, không head-to-head**.
2. **Định nghĩa "accuracy" khác nhau:** cấp ký tự / cấp biển / cấp session / WER. Rani 2024 (#13) chứng minh chỉ đổi cách xử lý khoảng trắng đã lệch 5.2 điểm → **phải công bố quy tắc chuẩn hoá chuỗi của mình.**
3. **Ghi cỡ test set cạnh mọi con số** — Moussaoui (#16, n=270) là ví dụ cảnh báo.
4. **Đừng trộn số vendor với số học thuật** — #17, #18 là claim tự công bố, chưa peer-review.

---

## F. Khoảng trống & việc cần làm

### Đã đóng ở pass 2 (2026-07-21)

- ✅ **Tác giả MAKE 2026 resolved** (Shalash, Khatab, El-Agamy, Elmokadem, Abouelsaad, Zaki, El-Sayed, Said) — Crossref, đã cập nhật `refs.bib`.
- ✅ **Verify claim INT8 của Sonnara từ bảng gốc trong PDF** — đúng, kèm nuance FP16 ở layer đầu/cuối.
- ✅ **Tác giả đầy đủ Safran / Arukonda / Tran & Bui / Sonnara** — Crossref.
- ✅ **Số sao + license + ngày push repo GitHub** — GitHub REST API (phát hiện 2 repo VN không có license).
- ✅ **Phát hiện Safran 2024 có web dashboard** — đã sửa bảng D.
- ✅ **Bổ sung paper VN mới:** Dang 2024 (CRNN+attention, bãi xe trong nhà) và repo VN mới `mrzaizai2k` (MIT).

### Còn mở

| # | Việc | Ưu tiên | Hạn |
|---|---|---|---|
| 1 | **Lấy PDF Tran & Bui 2025 qua thư viện UIT** — cần rõ: accuracy cấp ký tự hay cấp biển, cỡ test set, 0.478 s có gồm I/O không, tỷ lệ biển 1 vs 2 hàng | 🔴 **Cao** — là baseline #1, #2 | Trước tuần 9 |
| 2 | Lấy PDF Le 2023 (mAP 93%) — cần protocol đo và cỡ dataset | 🟡 Trung bình | Trước tuần 9 |
| 3 | Lấy PDF Dang 2024 — cần cỡ dataset bãi trong nhà + chi tiết WPOD-NET | 🟡 Trung bình | Tuần 4 (liên quan skew correction) |
| 4 | Bảng kết quả Pi 5 chi tiết của MAKE 2026 (MDPI chặn anti-bot) | 🟡 Trung bình | Trước tuần 9 |
| 5 | **IEEE 10014165** "ALPR Based on YOLO v4 for Smart Parking" ([IEEE Xplore](https://ieeexplore.ieee.org/document/10014165/)) — paywall; snippet gợi ý YOLOv4 + LINE-bot + claim "100% recognition rate" nhưng **chưa xác nhận được là của paper này → đã loại khỏi bảng baseline** | 🟢 Thấp | Nếu có thời gian |

### Phát hiện cần nêu như một luận điểm trong đồ án

**Không vendor thương mại VN nào (VETC, ePass, MParking, MegaParking, VietParking, TB-iParking) công bố % accuracy nhận dạng biển số dựa trên vision** — tất cả hoặc dùng RFID hoặc giữ kín. Cộng với việc **không paper VN nào trong khảo sát công bố hệ thống bãi xe đầy đủ có cả edge + backend + dashboard**, đồ án này sẽ là một trong số rất ít công trình ở VN có **con số accuracy vision-only công bố công khai, kèm protocol tái lập được**. Đây là câu định vị nên đưa vào cuối phần Tổng quan.

**Cảnh báo trích dẫn:** ePass "99.95%" là accuracy **RFID**, thường bị trích nhầm thành accuracy ALPR — **tuyệt đối không dẫn như accuracy vision.**

---

## Feeds vào

- **Chương Tổng quan:** nguồn VN (A1, B1, C1) dẫn dắt related work; quốc tế (A2–A4, B2, C2) mở rộng bối cảnh; lập luận chống cảm biến (A4, ba nguồn độc lập); luận điểm kiến trúc đa tầng (A2.4: 96.1% vs 83.9%); câu định vị ở mục F.
- **Chương Evaluation (tuần 9):** bảng E đầy đủ + bảng ánh xạ "mình báo cáo gì so với ai" + 4 lưu ý protocol bắt buộc.
- **Tuần 3 (detection, Nhật):** mốc mAP #3 (93%, biển xe máy VN); Zhu 2025 (#14) là hướng cải tiến nếu recall yếu.
- **Tuần 4+ (OCR, Nhật):** WPOD-NET (A1.2) cho skew correction; chuỗi tiền xử lý k-means+threshold+opening (A2.7); ma trận nhầm ký tự (A2.3 — "O" 38.96%).
- **Tuần 5 (dashboard, Đức):** feature list ParkPow (tag, alert overstay/ngoài giờ, drill-down, export CSV); QR động của Rani; layout React của `zxllxz2`; đối chiếu chéo VETC → alert bất khớp biển+màu.
- **Tuần 7 (optimization, Nhật):** bảng INT8 của Sonnara (#5) làm hình mẫu; **kỹ thuật giữ layer đầu/cuối ở FP16**.
- **Tuần 8 (edge, Đức):** spec camera ≥ 720p, ưu tiên 1080p (bằng chứng A2.2: 480p làm sập accuracy còn 23%); voting đa frame ở camera cổng (#7).
- **Pháp lý/kỹ thuật:** hai repo VN phổ biến không có license → **không tái sử dụng code**; dùng `fast-alpr` hoặc `mrzaizai2k` (MIT).
