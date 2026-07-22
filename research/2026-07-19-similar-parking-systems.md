# Khảo sát: Các hệ thống quản lý bãi xe thông minh và dashboard tương tự

**Ngày tạo:** 2026-07-19 · **Cập nhật lượt 2 (đào sâu primary source):** 2026-07-21
**Mode:** 1 (literature review) + 2 (so sánh tech/product)
**Mục đích:** tài liệu related-work cho Chương "Tổng quan" và tổng hợp số liệu định lượng từ các nghiên cứu liên quan.

**Thứ tự:** nguồn Việt Nam được trình bày trước trong mỗi mục do tương đồng về định dạng biển số, thị trường và quy định, rồi đến nguồn quốc tế. Mỗi công trình được đánh giá theo điểm mạnh và thiếu sót.

Metadata (tác giả, số trang, DOI) của mọi entry đã đối chiếu qua **Crossref API**, và số liệu kho mã nguồn qua **GitHub REST API**, ngày 2026-07-21 — không lấy từ blog hay trí nhớ.

---

## Hệ thống đề xuất

Mô tả độc lập kiến trúc hệ thống mà khảo sát này phục vụ — trình bày để xác lập phạm vi, không đặt trong tương quan so sánh với các công trình ở những mục sau.

| Thành phần | Công nghệ | Chức năng |
|---|---|---|
| Phát hiện | YOLOv8 / YOLO26 (ultralytics) | Phát hiện xe và biển số Việt Nam theo cascade hai giai đoạn |
| Nhận dạng (OCR) | PaddleOCR / EasyOCR | Đọc chuỗi ký tự trên biển số, hỗ trợ biển 1 hàng và 2 hàng |
| Phân loại màu biển | OpenCV — HSV + CLAHE | Phân loại nền biển: trắng (tư nhân), vàng (kinh doanh), xanh (cơ quan) |
| Backend | FastAPI + PostgreSQL | Khớp session vào/ra, tính phí theo thời lượng |
| Dashboard | React | Trực quan hóa occupancy, log session, thống kê |
| Triển khai edge | Raspberry Pi 5, ONNX Runtime, INT8 | Suy luận tại biên, mục tiêu < 2 s/xe end-to-end |

**Ràng buộc thiết kế:** toàn bộ pipeline (model + FastAPI + CSDL) chạy trên một thiết bị edge Raspberry Pi 5 duy nhất. Biển số và ảnh xe được xử lý như dữ liệu cá nhân theo Luật Bảo vệ dữ liệu cá nhân (hiệu lực 01/01/2026): kiểm soát truy cập bản ghi, mã hóa trường nhạy cảm, và tự động xóa bản ghi sau thời hạn lưu trữ quy định kể từ khi xe rời bãi.

---

## Quy ước mức độ evidence

Mỗi entry ghi rõ mức độ truy cập được của nguồn, làm cơ sở cho độ tin cậy khi trích dẫn.

| Ký hiệu | Nghĩa | Cách dùng khi viết đồ án |
|---|---|---|
| **Full text** | Đã tiếp cận full text (PDF/HTML), số liệu lấy từ bảng gốc | Trích dẫn được cả con số cụ thể và protocol đo |
| **Abstract** | Chỉ có abstract + metadata Crossref | Trích được số liệu headline, không trích chi tiết protocol |
| **Paywall** | Chưa tiếp cận được full text | Số liệu ở mức thứ cấp; bổ sung PDF trước khi trích chính thức |

---

## A. Hệ thống học thuật

### A1. Nhận dạng biển số Việt Nam — related work trọng tâm

Nhóm nguồn tương đồng nhất về định dạng biển, thị trường và phần cứng — cung cấp baseline nhận dạng và phát hiện cho biển số Việt Nam.

---

#### A1.1 · Tran & Bui 2025 — LPR Việt Nam trên Raspberry Pi 4 · **Paywall**

| Mục | Nội dung |
|---|---|
| **Trích dẫn** | V. Tran and T. Bui, "Implementation of a License Plate Recognition System in Vietnam Using Embedding Devices," in *Multi-disciplinary Trends in Artificial Intelligence (MIWAI 2024)*, LNCS, Springer, Singapore, 2025, pp. 231–243. |
| **DOI / link** | [10.1007/978-981-96-0695-5_19](https://link.springer.com/chapter/10.1007/978-981-96-0695-5_19) · [mirror ACM DL](https://dl.acm.org/doi/abs/10.1007/978-981-96-0695-5_19) |
| **Tác giả (verified)** | Vanha Tran; Thiloan Bui — Crossref 2026-07-21 |
| **Kiến trúc** | 2 giai đoạn: **SSD-MobileNetV2** detect biển số → **YOLOv8-nano** nhận dạng ký tự (OCR-as-detection, không dùng OCR engine) |
| **Phần cứng** | Raspberry Pi 4 Model B + Pi Camera V2 (8 MP) |
| **Số liệu** | Accuracy nhận dạng trung bình **95.68%**; thời gian xử lý trung bình **0.478 s/ảnh** |
| **Code / dataset** | N/A |
| **Trạng thái nguồn** | N/A (full text chưa tiếp cận được; số liệu ở mức thứ cấp) |

**Điểm mạnh:** hiếm gặp — nhận dạng biển số Việt Nam đo trực tiếp trên phần cứng edge Raspberry Pi; báo cáo đồng thời độ chính xác (95.68%) và thời gian xử lý (0.478 s/ảnh) ở cùng điều kiện triển khai.
**Thiếu sót:** không phân định độ chính xác ở cấp ký tự hay cấp biển; không nêu cỡ tập test; không rõ 0.478 s có bao gồm I/O camera; không phân biệt tỷ lệ biển 1 hàng và 2 hàng; dừng ở nhận dạng, không có quản lý session hay tính phí.
**BibTeX:** `tran2025vietnamlpr`

---

#### A1.2 · Dang và cộng sự 2024 — CRNN + attention, dataset bãi xe trong nhà ở VN · **Abstract**

| Mục | Nội dung |
|---|---|
| **Trích dẫn** | L. T. A. Dang, V. D. Ngoc, P. C. L. T. Vu, N. N. Truong, P. T. Bao, and T. D. Trinh, "Vietnam Vehicle Number Recognition Based on an Improved CRNN with Attention Mechanism," *Int. J. Intelligent Transportation Systems Research*, vol. 22, pp. 374–389, 2024. |
| **DOI / link** | [10.1007/s13177-024-00402-7](https://link.springer.com/article/10.1007/s13177-024-00402-7) · [TRID](https://trid.trb.org/View/2414278) |
| **Nhóm** | Nhóm VN (Pham The Bao — Saigon University); công bố 31/5/2024; 7 citation (Semantic Scholar, 2026-07-21) |
| **Kiến trúc** | 3 bước: **YOLO** detect xe → **WPOD-NET** trích biển số (chuyên xử lý biển xiên góc) → **CRNN cải tiến** train đồng thời **CTC + attention** để đọc ký tự |
| **Dataset** | Tự thu tại **bãi đỗ xe trong nhà** ở VN; cỡ dataset N/A |
| **Số liệu** | **Word Error Rate (WER) = 0.014** trong tác vụ OCR |
| **Trạng thái nguồn** | N/A (chỉ có abstract + metadata Crossref) |

**Điểm mạnh:** dataset thu tại bãi đỗ trong nhà — ngữ cảnh sát với bài toán quản lý bãi xe; WPOD-NET xử lý tốt biển xiên góc; huấn luyện CRNN đồng thời với CTC và attention cho WER rất thấp (0.014).
**Thiếu sót:** cỡ dataset và protocol đo N/A; chỉ dừng ở khâu nhận dạng, không mở rộng sang session hay tính phí.
**BibTeX:** `dang2024vietnamcrnn`

---

#### A1.3 · Le và cộng sự 2023 — biển số xe máy VN, YOLOv8 3 tầng · **Paywall**

| Mục | Nội dung |
|---|---|
| **Trích dẫn** | D. H. Le, D. Mazumder, L.-D. Quach, S. Banerjee, and V.-D. Nguyen, "Robust Vietnam's Motorcycle License Plate Detection and Recognition Using Deep Learning Model," in *Future Data and Security Engineering (FDSE 2023)*, CCIS, Springer, Singapore, 2023, pp. 64–75. |
| **DOI / link** | [10.1007/978-981-99-8296-7_5](https://link.springer.com/chapter/10.1007/978-981-99-8296-7_5) |
| **Tác giả (verified)** | Duc Hoa Le; Debarshi Mazumder; Luyl-Da Quach; Shreya Banerjee; Vinh Dinh Nguyen — Crossref 2026-07-21 |
| **Kiến trúc** | YOLOv8 **3 tầng**: detect xe máy → detect biển số **bên trong bbox xe máy** → nhận dạng biển |
| **Dataset** | Dataset biển số xe máy VN trên Roboflow |
| **Số liệu** | **mAP 93%** (tốt nhất, sau 300 epoch); số liệu tốc độ N/A |
| **Ứng dụng đích** | Phạt nguội vi phạm tốc độ |
| **Trạng thái nguồn** | N/A (full text chưa tiếp cận được) |

**Điểm mạnh:** cung cấp baseline mAP 93% trực tiếp cho biển 2 hàng của xe máy Việt Nam — loại biển khó; kiến trúc cascade phát hiện xe trước, biển sau là thiết kế phổ biến và hợp lý.
**Thiếu sót:** không có số liệu tốc độ nên chưa đánh giá được khả năng triển khai real-time; protocol đo và cỡ dataset N/A.
**BibTeX:** `le2023motorcycleplate`

---

#### A1.4 · Tran-Anh và cộng sự 2023 — LPR đa góc nhìn (PTIT) · **Abstract** (arXiv mở)

| Mục | Nội dung |
|---|---|
| **Trích dẫn** | D. Tran-Anh, K. L. Tran, and H.-N. Vu, "License Plate Recognition Based On Multi-Angle View Model," arXiv:2309.12972, 2023. |
| **Link** | [arXiv:2309.12972](https://arxiv.org/abs/2309.12972) — truy cập tự do |
| **Kiến trúc** | Fuse đặc trưng corner-point/diện tích qua **3 góc nhìn** trước khi nhận dạng bằng **CnOCR** |
| **Dataset** | **PTITPlates** (tự thu, Học viện PTIT) + Stanford Cars |
| **Số liệu** | N/A (abstract khẳng định vượt trội nhưng không công bố con số headline) |

**Điểm mạnh:** hướng tiếp cận đa góc nhìn nhằm tăng độ bền theo góc chụp; xây dựng bộ dữ liệu PTITPlates riêng; toàn văn mở trên arXiv.
**Thiếu sót:** không công bố số liệu định lượng nên không thể dùng làm baseline so sánh.
**BibTeX:** `trananh2023multiangle`

---

#### A1.5 · UIT MAPR 2018 — Cuộc thi nhận dạng biển số xe máy VN · **Dataset**

| Mục | Nội dung |
|---|---|
| **Nguồn** | MAPR 2018 organizers, "Vietnamese Bike License Plate Recognition Challenge," 1st Int. Conf. on Multimedia Analysis and Pattern Recognition, UIT, 2018. [mapr.uit.edu.vn](https://mapr.uit.edu.vn/2018/vietnamese-bike-license-plate-recognition) |
| **Dataset** | **3.000 ảnh xe máy chụp tại bãi giữ xe khách sạn ở VN** — 2.000 train / 1.000 test |
| **Task** | Detect biển số (bbox) + nhận dạng text |
| **Trạng thái** | N/A (link tải dataset không truy cập được) |

**Điểm mạnh:** benchmark biển số xe máy Việt Nam đặt tại chính bối cảnh bãi giữ xe; xác lập gốc nghiên cứu tại UIT.
**Thiếu sót:** dataset N/A (không tải được), nên chỉ có giá trị dẫn nguồn lịch sử.
**BibTeX:** `mapr2018challenge`

---

### A2. Hệ thống bãi xe / ALPR quốc tế — full pipeline

Các hệ thống hoàn chỉnh hơn — nhiều công trình tích hợp cả session, tính phí, dashboard và triển khai edge — cùng những mẫu protocol đo minh bạch.

---

#### A2.1 · Pradhan và cộng sự 2025 — bãi xe IoT + ALPR + thanh toán trên Raspberry Pi · **Full text**

Hệ thống hoàn chỉnh nhất trong khảo sát ở cấp độ tích hợp: edge Pi + ALPR + khớp session + tính phí + occupancy.

| Mục | Nội dung |
|---|---|
| **Trích dẫn** | G. Pradhan, M. R. Prusty, V. S. Negi, and S. Chinara, "Advanced IoT-integrated parking systems with automated license plate recognition and payment management," *Scientific Reports*, vol. 15, art. 2388, 2025. |
| **DOI / link** | [10.1038/s41598-025-86441-w](https://www.nature.com/articles/s41598-025-86441-w) · **full text mở:** [PMC11742719](https://pmc.ncbi.nlm.nih.gov/articles/PMC11742719/) |
| **Đơn vị** | Vellore Institute of Technology + NIT Rourkela (Ấn Độ) |

**Phần cứng (từ full text):**
- **Raspberry Pi 4 Model B** — edge device quản lý **4 camera** (USB + cổng Pi camera)
- **ESP32 (ESP-WROOM-32)** — **một con mỗi ô đỗ**, kèm pin riêng
- Cảm biến IR: ngoài trời gắn dưới đất "giữa hai bánh xe"; trong nhà gắn tường
- Camera: yêu cầu tối thiểu **1080p, auto-focus, HDR**
- **Smart Metering Display (SMD)** ở cổng ra hiển thị phí

**Stack phần mềm:** YOLO (không nêu version) + **Tesseract OCR** + tiền xử lý OpenCV (Gaussian blur → threshold → Canny → HSV/grayscale) + **SQL Server (SSMS) / SQLite**.
**Kiến trúc 3 module:** VRS (camera vào/ra ghi biển + timestamp) · VPDS (IR + ESP32 + camera mỗi ô, tọa độ ô liên kết với cảm biến để dual verification) · SMD (đo thời lượng + hiển thị phí).
**Logic tính phí:** `Phí = Thời lượng đỗ × Chi phí mỗi giây`, có dynamic pricing theo giờ cao/thấp điểm.

**Số liệu và protocol đo:**

| Metric | Giá trị | Điều kiện đo |
|---|---|---|
| Nhận dạng biển số | **95%** | Ban ngày |
| Nhận dạng biển số | **90%** | Ánh sáng yếu |
| Nhận dạng biển số | **93%** | Góc 45° |
| Detect xe | **88%** | Khoảng cách 1.5–3 m |
| **Khớp biển số tổng thể** | **88.9%** | trên 100 test case |
| Sai số theo dõi occupancy | **< 5%** | so với đếm thủ công |
| Giảm lỗi tính tiền | **90%** | so với phương pháp cũ |

Con số khớp biển số 88.9% (n=100) là một trong số ít chỉ số đo ở cấp hệ thống trong tài liệu khảo sát. Code/dataset: N/A.

**Điểm mạnh:** tích hợp trọn vẹn edge, ALPR, session, tính phí động và theo dõi occupancy; báo cáo độ chính xác *theo điều kiện* (95% ngày / 90% ánh sáng yếu / 93% góc 45°) thay vì một con số đơn lẻ; sai số occupancy < 5%.
**Thiếu sót:** yêu cầu ESP32 + cảm biến IR cho mỗi ô đỗ, chi phí và bảo trì phần cứng cao; OCR Tesseract yếu với biển số ngoài Latin chuẩn; không tách bạch độ chính xác cấp ký tự và cấp biển; không phân tích nguyên nhân các test case thất bại; code/dataset N/A.
**BibTeX:** `pradhan2025iotparking`

---

#### A2.2 · Ammar và cộng sự 2023 — nhận dạng xe + biển số đa tầng, edge tại cổng bãi xe · **Full text**

Công trình học thuật gần nhất cho use-case access-control chạy trên edge; đoạt 2 giải thưởng (2021, 2022).

| Mục | Nội dung |
|---|---|
| **Trích dẫn** | A. Ammar, A. Koubaa, W. Boulila, B. Benjdira, and Y. Alhabashi, "A Multi-Stage Deep-Learning-Based Vehicle and License Plate Recognition System with Real-Time Edge Inference," *Sensors*, vol. 23, no. 4, p. 2120, 2023. |
| **DOI / link** | [10.3390/s23042120](https://doi.org/10.3390/s23042120) · **full text mở:** [PMC9966104](https://pmc.ncbi.nlm.nih.gov/articles/PMC9966104/) |
| **Nơi triển khai** | Cổng bãi xe nhân viên + cổng chính campus Prince Sultan University, Riyadh |

**Pipeline 5 tầng (có input size):**
1. **YOLOv4** (416×416) detect xe + biển số — nguồn video **RTSP stream**
2. **Xception** (pretrain ImageNet) + avg-pool 4×4 + 3 FC layer → phân loại **196 lớp đời xe**
3. Nhận dạng ký tự — 2 phương án: *Model 1* YOLOv3 (320×320) + MobileNetV2 CNN (54 lớp ký tự); ***Model 2b (được chọn)*** YOLOv4 (416×416) → **27 lớp ký tự đôi**
4. **DeepSORT tùy biến** + cơ chế **voting qua nhiều frame**
5. Tối ưu bằng **NVIDIA TensorRT** (quantization + layer/tensor fusion)

**Dataset (tất cả tự thu, biển Saudi):** detect xe+biển 203 ảnh / 819 xe / 246 biển · phân loại đời xe 41.521 ảnh, 196 lớp · detect ký tự đơn 373 ảnh crop, 5.193 ký tự · phân loại ký tự 18.422 ảnh · detect ký tự đôi 593 ảnh, 3.827 ký tự đôi · **đánh giá: 2 video (11m18s + 21m28s) + 100 ảnh tĩnh**.

**Số liệu và protocol (IoU 0.5):**

| Metric | Giá trị |
|---|---|
| mAP detect (tổng) | **74.1%** — AP xe 67.6%, AP biển 80.7% |
| Phân loại đời xe | precision 97.5%, recall/F1/accuracy 97.3% |
| Detect ký tự đơn / đôi (val) | mAP 99.8% / 99.0% |
| **Ảnh tĩnh** (Model 2b) | ký tự đúng 92.5%, biển đầy đủ đúng **53%**, 9.5 FPS |
| **Video 1** | ký tự 81.9%, biển đầy đủ **67%**, 14.4 FPS |
| **Video 2** | ký tự 95%, biển đầy đủ **80%**, 18.4 FPS |
| **Tổng hợp** | ký tự **88.6%**, biển đầy đủ **74%**, **17.1 FPS** trên Jetson Xavier AGX |

**Ba phát hiện định lượng đáng chú ý:**
1. **Voting theo frame cải thiện độ chính xác đáng kể với chi phí thấp:** "accuracy jumps from **29% when using a single frame to 69% when using a maximum of 35 frames**". Xử lý video thay vì ảnh tĩnh tăng tương đối 40% cho biển số.
2. **Độ phân giải camera có ảnh hưởng quyết định** (cùng Video 2):

   | Độ phân giải | Miss biển | Ký tự đúng | Biển đúng | FPS |
   |---|---|---|---|---|
   | 1920×1080 | 0% | 95% | **80%** | 18.4 |
   | 1280×720 | 2% | 91.2% | 72% | 19.5 |
   | 720×480 | 20% | 79.3% | **23%** | 21.2 |

   Ở 480p, độ chính xác biển giảm mạnh từ 80% xuống 23% — cho thấy ngưỡng thực dụng là ≥ 720p, tốt hơn ở 1080p.
3. **Khoảng cách giữa validation và thực tế:** ký tự val 99.8% nhưng biển đầy đủ thực tế chỉ 74% — minh chứng cần báo cáo cả hai cấp độ đo.

**Điểm mạnh:** pipeline 5 tầng đầy đủ, đánh giá trên cả video lẫn ảnh tĩnh; định lượng rõ hiệu ứng voting đa frame và độ phân giải camera; tối ưu bằng TensorRT cho suy luận edge.
**Thiếu sót:** khoảng cách lớn giữa độ chính xác validation (99.8%) và thực tế (74%); 14% xe có đời không nằm trong tập train; vấn đề bảo mật và quyền riêng tư của biển số chỉ được nêu như hướng phát triển tương lai; code/dataset N/A.
**BibTeX:** `ammar2023multistage`

---

#### A2.3 · Al-batat và cộng sự 2022 — ALPR end-to-end, có mã nguồn mở · **Full text · MIT code**

Công trình duy nhất trong khảo sát đồng thời có full text mở, mã nguồn chạy được và đánh giá trên 5 dataset công khai.

| Mục | Nội dung |
|---|---|
| **Trích dẫn** | R. Al-batat, A. Angelopoulou, S. Premkumar, J. Hemanth, and E. Kapetanios, "An End-to-End Automated License Plate Recognition System Using YOLO Based Vehicle and License Plate Detection with Vehicle Classification," *Sensors*, vol. 22, no. 23, p. 9477, 2022. |
| **DOI / link** | [10.3390/s22239477](https://doi.org/10.3390/s22239477) · **full text mở:** [PMC9737602](https://pmc.ncbi.nlm.nih.gov/articles/PMC9737602/) |
| **Mã nguồn** | [github.com/RedaAlb/alpr-pipeline](https://github.com/RedaAlb/alpr-pipeline) — MIT licence, Darknet framework (GitHub API 2026-07-21: 9★/3 fork) |

**Pipeline (có input size):** YOLOv2 (608×416) detect xe → YOLOv4-tiny (416×416) detect biển → YOLOv4-tiny (**352×128**, chọn theo "average aspect ratio (w/h) of all LP patches across all datasets is 2.86") nhận dạng ký tự → ResNet50 phân loại loại xe.

**Dataset — 5 tập công khai, 7.290 mẫu, đa vùng:**

| Dataset | Vùng | Mẫu | Độ phân giải |
|---|---|---|---|
| Caltech Cars | Mỹ | 124 | 896×592 |
| English LP | EU | 509 | 640×480 |
| OpenALPR EU | EU | 108 | đa dạng |
| AOLP | Đài Loan | 2.049 | đa dạng |
| UFPR-ALPR | Brazil | 4.500 | 1920×1080 |

**Protocol đo (minh bạch):** 36 lớp ký tự (0-9, A-Z); Precision = TP/(TP+FP), Recall = TP/(TP+FN); **IoU riêng cho từng tầng: VD 0.25, LPD 0.65, LPR 0.5**; kết quả trung bình qua 5 lần chia train/val/test ngẫu nhiên (0.7/0.2/0.1).

| Tầng | Precision | Recall |
|---|---|---|
| Detect xe (VD) | 99.71% | 99.90% |
| Detect biển (LPD) | 99.16% | 99.36% |
| Nhận dạng (LPR, tách riêng) | **99.68%** | 97.69% |
| **Toàn pipeline** | **90.3%** accuracy trung bình (cấp ký tự, qua cả 5 dataset) | |
| Phân loại loại xe (ResNet50) | **98.22%** (3 lớp: xe khẩn cấp 449 / xe tải 374 / khác 831) | |

**Tốc độ (GTX 1060 — GPU đời thấp):** 1 xe **18 FPS**, 2 xe 13 FPS, 3 xe 11 FPS. Tác giả tự lưu ý kết quả "are not a fair comparison to other methods because a very low-end GPU was used".
**Failure case:** ký tự khó nhất "O" chỉ đạt 38.96% AP ("K" 83.86%, "M" 86.50%, "Q" 70.84%); UFPR-ALPR chỉ 62.06% theo frame, tăng lên 73.33% với consensus 3 frame; test set nhỏ ở vài dataset ảnh hưởng lớn tới recall.

**Điểm mạnh:** hiếm gặp — đồng thời có toàn văn mở, mã nguồn giấy phép MIT và đánh giá đa vùng trên 5 dataset công khai; protocol đo minh bạch (IoU riêng từng tầng, trung bình 5-fold); phân tích failure case ở cấp ký tự (nhóm ký tự dễ nhầm như "O").
**Thiếu sót:** đo trên GPU đời thấp nên số FPS không đại diện; chủ ý không dùng post-processing rule; test set nhỏ ở một số dataset làm nhiễu recall.
**BibTeX:** `albatat2022endtoend` · mã nguồn `redalb2022alprcode`

---

#### A2.4 · Safran và cộng sự 2024 — YOLOv8 đa tầng kèm web dashboard · **Abstract**

| Mục | Nội dung |
|---|---|
| **Trích dẫn** | M. Safran, A. Alajmi, and S. Alfarhood, "Efficient Multistage License Plate Detection and Recognition Using YOLOv8 and CNN for Smart Parking Systems," *Journal of Sensors*, vol. 2024, art. 4917097, pp. 1–18, 2024. |
| **DOI / link** | [10.1155/2024/4917097](https://doi.org/10.1155/2024/4917097) |
| **Tác giả (verified)** | Mejdl Safran; Abdulmalik Alajmi; Sultan Alfarhood — Crossref 2026-07-21 |
| **Kiến trúc** | **YOLOv5** detect biển → **YOLOv8** detect ký tự → **CNN mới** phân loại ký tự |
| **Dataset** | Tự thu, biển số **Saudi**; dùng camera giám sát có sẵn trong bãi (không lắp thêm phần cứng) |
| **Số liệu** | Đa tầng **96.1%** vs single-stage **83.9%**; nhận dạng ký tự CNN 97% |
| **Dashboard** | *"integrated into a **web-based dashboard** for real-time visualization and statistical analysis of car park occupancy and vehicle movement with an acceptable time efficiency"* |

**Điểm mạnh:** cung cấp bằng chứng định lượng cho kiến trúc đa tầng (96.1% so với 83.9% ở single-stage); tích hợp web dashboard trực quan hóa occupancy và luồng xe; tận dụng camera giám sát có sẵn nên không thêm phần cứng. Abstract nêu thẳng hạn chế của giải pháp cảm biến: "entail high installation and maintenance costs and limited functionality in tracking vehicle movement".
**Thiếu sót:** full text N/A (chỉ có abstract); dataset biển Saudi, khác định dạng biển Việt Nam.
**BibTeX:** `safran2024multistage`

---

#### A2.5 · Rani và cộng sự 2024 — IPS: module vào/ra + thanh toán QR · **Abstract**

| Mục | Nội dung |
|---|---|
| **Trích dẫn** | R. Rani, S. Kumar, S. K. Pippal, M. Gund, U. Chaudhari, R. Agrawal, M. Dalsaniya, and L. Verma, "IPS: Intelligent Parking System Using YOLO and Image Processing," *Int. J. Transport Development and Integration*, vol. 8, no. 3, pp. 447–453, 2024. |
| **DOI / link** | [10.18280/ijtdi.080308](https://doi.org/10.18280/ijtdi.080308) · [Acadlore](https://www.acadlore.com/article/IJTDI/2024_8_3/ijtdi.080308) |
| **Kiến trúc** | **YOLOv5m** detect biển + OCR; module vào ghi biển + timestamp, tài xế chọn block; module ra tính phí theo thời lượng và sinh **QR code động thanh toán không tiếp xúc** |
| **Dataset** | 3.500 ảnh, chia 70/30 |
| **Số liệu** | LPR **97.11%** (không tính khoảng trắng) / **91.91%** (tính cả khoảng trắng); recall 97.25% |

**Điểm mạnh:** quy trình vào/ra và tính phí hoàn chỉnh, bổ sung thanh toán QR động không tiếp xúc; minh họa rõ mức độ độ chính xác phụ thuộc quy tắc chuẩn hóa chuỗi (97.11% so với 91.91% chỉ do cách xử lý khoảng trắng).
**Thiếu sót:** full text N/A (abstract); không triển khai edge.
**BibTeX:** `rani2024ips`

---

#### A2.6 · Arukonda và cộng sự 2026 — YOLOv8 + OCR phân bổ chỗ đỗ · **Abstract**

| Mục | Nội dung |
|---|---|
| **Trích dẫn** | S. Arukonda, G. S. Jayanth, A. S. S. Koushik, T. Sarupya, P. V. Kumar, and K. B. Reddy, "Real-Time Vehicle Number Plate Recognition and Smart Parking Allocation Using YOLOv8 and OCR for Intelligent Urban Mobility," *Int. J. Intelligent Transportation Systems Research*, 2026. |
| **DOI / link** | [10.1007/s13177-025-00612-7](https://doi.org/10.1007/s13177-025-00612-7) |
| **Tác giả (verified)** | 6 tác giả đầy đủ qua Crossref 2026-07-21 |
| **Kiến trúc** | YOLOv8 detect biển trên video trực tiếp → EasyOCR + Tesseract → hậu xử lý sửa ký tự + **validate định dạng theo quốc gia** → phân bổ chỗ theo rule (20 chỗ, cánh Đông/Tây) → ghi log **Excel** |
| **Dataset** | Tự gán nhãn, 5.000+ ảnh |
| **Số liệu** | Detect **98.5%**, precision 98.2%, recall 97.8%, F1 98.0%; latency 50 ms/frame (phần cứng N/A) |

**Điểm mạnh:** bổ sung bước validate định dạng biển theo quốc gia; độ chính xác phát hiện cao (98.5%).
**Thiếu sót:** latency 50 ms không nêu phần cứng nên không so sánh được; backend chỉ ghi log Excel, không có CSDL thực; full text N/A (abstract).
**BibTeX:** `arukonda2026smartparking`

---

#### A2.7 · Moussaoui và cộng sự 2024 — YOLOv8 + EasyOCR · **Abstract**

| Mục | Nội dung |
|---|---|
| **Trích dẫn** | H. Moussaoui, N. El Akkad, M. Benslimane, W. El-Shafai, A. Baihan, C. Hewage, and R. S. Rathore, "Enhancing automated vehicle identification by integrating YOLO v8 and OCR techniques...," *Scientific Reports*, vol. 14, art. 14389, 2024. |
| **DOI / link** | [10.1038/s41598-024-65272-1](https://doi.org/10.1038/s41598-024-65272-1) |
| **Pipeline (từ abstract)** | Thu **270 ảnh từ internet** → gán nhãn bằng **CVAT** → YOLOv8 detect vùng biển → **k-means clustering + thresholding + phép mở (opening) morphology** làm rõ ký tự → OCR → sinh file text kèm mã quốc gia |
| **Số liệu** | Detect/precision/recall **99%**, nhận dạng ký tự **98%**; metric dùng: precision, recall, F1, CLA |

**Điểm mạnh:** chuỗi tiền xử lý k-means + threshold + opening là tham chiếu hữu ích cho khâu làm rõ ảnh biển; xác nhận tính khả thi của cặp YOLOv8 + EasyOCR.
**Thiếu sót:** tập test chỉ 270 ảnh nên con số 99% nhiều khả năng lạc quan so với thực tế; không có số liệu latency/FPS; full text N/A (abstract).
**BibTeX:** `moussaoui2024yolov8ocr`

---

### A3. ALPR trên edge — bằng chứng lượng hoá cho INT8

Nhóm nguồn định lượng đánh đổi giữa độ chính xác, tốc độ và điện năng khi lượng tử hóa INT8 cho suy luận trên thiết bị biên.

---

#### A3.1 · Sonnara và cộng sự 2025 — "Light-Edge" INT8 trên Jetson Nano · **Full text · CC-BY**

Nguồn định lượng đầy đủ nhất cho câu hỏi INT8 mất bao nhiêu độ chính xác và được bao nhiêu tốc độ.

| Mục | Nội dung |
|---|---|
| **Trích dẫn** | F. Sonnara, H. Chihaoui, and F. Filali, "Efficient real-time license plate recognition using deep learning on edge devices," *J. Real-Time Image Processing*, vol. 22, no. 5, art. 159, 2025. |
| **DOI / link** | [10.1007/s11554-025-01738-3](https://doi.org/10.1007/s11554-025-01738-3) — **CC-BY 4.0, PDF mở** |
| **Kiến trúc** | **Light-Edge**: backbone **ResNet-18 + FPN dùng chung**, head detect **anchor-free**, head nhận dạng **CTC** — một network vừa detect vừa đọc. Khối **1×1 channel-fusion** loại bỏ 28% số convolution. |
| **Ràng buộc thiết kế** | Phần cứng roadside < 10 W, RAM hạn chế, kết nối chập chờn → loại bỏ phương án offload lên cloud |

**Dataset — CCPD (Chinese City Parking Dataset):** tổng **290.316 ảnh** 720×1280, camera cố định ở Bắc Kinh (2016–2018); tên file mã hoá sẵn 4 góc biển + chuỗi 7 ký tự. Official split: 200.000 train / 20.000 val / 20.000 test, cộng 6 subset đánh giá (Blur, FN, Rotate, Tilt, Weather, Challenge = 50.316 ảnh). Nhóm tác giả huấn luyện trên 30.000 ảnh + 2.000 val (giới hạn RAM 4 GB của Jetson Nano) nhưng luôn đánh giá trên đủ 20.000 ảnh test. Đa dạng: 61.4% ngày / 38.6% đêm; quay trong mặt phẳng ±60°, nghiêng ngoài mặt phẳng tới 45°; bề rộng biển 40–420 px (TB 138 px). **Training:** Adam, 38 epoch, batch 32, α=0.9, lr 1e-3 chia 10 mỗi 10 epoch, early-stop 3 epoch.

**Bảng 2 — kết quả trên Jetson Nano** (export ONNX → TensorRT 8.5, input 1×1280×720):

| Phương pháp | Model (MB) | FPS ↑ | mAP (%) ↑ | Điện (W) ↓ |
|---|---|---|---|---|
| TE2E | 145 | 2.1 | 88.4 | 9.5 |
| RPNet | 92 | 11.3 | 90.0 | 10.1 |
| AF-Net | 56 | 8.1 | **97.2** | 8.8 |
| YOLOv8-MobileLPR (re-impl.) | 68 | 9.5 | 89.8 | 9.3 |
| **Light-Edge (FP32, trước tối ưu)** | 38 | 3.1 | 90.6 | 5.4 |
| **Light-Edge (TensorRT INT8)** | 38 | **14.2** | 90.2 | **4.8** |

**Kết luận về INT8 (nguyên văn):** *"INT8 quantisation and kernel fusion raise throughput from 3.1 fps to 14.2 fps yet cost only −0.4 pp mAP"* → tăng tốc **4.6×**, chỉ mất **0.4 điểm mAP**. Paper giải thích cơ chế: *"TensorRT leaves the first and last layers in FP16, preserving representational fidelity where it matters most"* — tức lượng tử hóa hỗn hợp (mixed-precision) chứ không phải INT8 thuần, gợi ý kỹ thuật giữ layer đầu/cuối ở độ chính xác cao.

**Cảnh báo trích dẫn:** throughput-per-watt được paper ghi ba lần không nhất quán — "tripling" (§1), "0.57 → 2.96 fps·W⁻¹" (= 5.2×, §3) và "improves 13×" (§5); không nên trích chỉ số này. Các số FPS/mAP/W trong Bảng 2 thì nhất quán và dùng được.

**Điểm mạnh:** cung cấp bảng đối chiếu FP32 và INT8 đầy đủ trên cùng thang đo (model size, FPS, mAP, điện năng); chỉ ra kỹ thuật giữ layer đầu/cuối ở FP16 để bảo toàn độ chính xác; toàn văn CC-BY mở.
**Thiếu sót:** tồn tại mâu thuẫn nội tại ở chỉ số throughput-per-watt; huấn luyện chỉ trên 30.000 ảnh do giới hạn RAM; phần cứng Jetson Nano khác lớp thiết bị CPU-only.
**BibTeX:** `sonnara2025lightedge`

---

#### A3.2 · Zhu và cộng sự 2025 — YOLOv8n cải tiến cho biển số nhỏ · **Abstract**

| Mục | Nội dung |
|---|---|
| **Trích dẫn** | R. Zhu, Q. He, H. Jin, Y. Han, and K. Jiang, "License Plate Detection Based on Improved YOLOv8n Network," *Electronics*, vol. 14, no. 10, p. 2065, 2025. |
| **DOI / link** | [10.3390/electronics14102065](https://www.mdpi.com/2079-9292/14/10/2065) |
| **Cải tiến** | Thiết kế lại **C2f**, **SPPF**, và **detection head**; thay **CIoU → WIoU** loss |
| **Dataset** | Tự thu, cảnh giám sát, đa dạng ánh sáng/nền/góc/loại xe (không công bố cỡ — N/A) |
| **Số liệu** | mAP@0.5 **90.9% → 94.4%**; precision 90.2% → 92.8%; recall 82.9% → 87.9%; **tham số giảm 3.1M → 2.1M**; **86 FPS** |

**Điểm mạnh:** đồng thời tăng mAP (90.9% → 94.4%) và giảm 32% số tham số (3.1M → 2.1M), tức mô hình nhẹ hơn nhưng chính xác hơn — phù hợp bài toán biển nhỏ, xiên, nền phức tạp.
**Thiếu sót:** full text N/A (abstract); dataset tự thu không công bố nên khó tái lập.
**BibTeX:** `zhu2025licenseplate`

---

### A4. Bãi xe dựa trên cảm biến IoT — đối chứng với hướng vision

Ba nguồn độc lập cùng chỉ ra chi phí lắp đặt và bảo trì cao của cảm biến từng-ô, làm căn cứ cho hướng tiếp cận dựa trên camera.

- **Ndunda & Nicolas 2026** — E. Ndunda and A. Nicolas, "Smart On-Street Parking: Survey of Actual Implementations in Cities and Insights from Practitioners," [arXiv:2602.06517](https://arxiv.org/abs/2602.06517), 2026. Khảo sát ~25 triển khai thực tế và phỏng vấn practitioner tại 10 thành phố. Phát hiện: cảm biến từ chôn dưới đất đầu thập niên 2010 hỏng phần cứng khiến nhiều dự án ngừng sớm; xu hướng dịch sang camera tĩnh (phủ nhiều chỗ đỗ trên mỗi thiết bị) và camera ALPR tuần tra. BibTeX: `ndunda2026onstreet`
- **Safran 2024** (A2.4) độc lập xác nhận: cảm biến "entail high installation and maintenance costs and limited functionality in tracking vehicle movement".
- **Pradhan 2025** (A2.1) là ví dụ hybrid: IR mỗi ô kết hợp ALPR — đổi lấy sai số occupancy < 5% bằng chi phí một ESP32 + IR cho mỗi ô.
- Tham khảo ngành (phi học thuật): cảm biến siêu âm mỗi ô quảng cáo ~97% trong nhà nhưng cần lắp overhead có nguồn ở mỗi chỗ; camera phủ nhiều chỗ và đồng thời cho occupancy + biển số + dwell time ([Parking BOXX](https://parkingboxx.com/blog/technology/parking-occupancy-sensors-explained/)).

**Nhận xét tổng hợp:** ba nguồn độc lập — khảo sát thực địa (Ndunda), công bố học thuật (Safran) và chi phí phần cứng (Pradhan) — cùng cho thấy giải pháp cảm biến từng-ô tốn kém và khó bảo trì. Đây là căn cứ cho hướng tiếp cận dựa trên camera trong bài toán bãi xe.

---

## B. Sản phẩm thương mại

### B1. Vendor Việt Nam

| Sản phẩm | Claim ALPR | Edge | Dashboard / tính năng | Giá (2026-07-19) |
|---|---|---|---|---|
| **VETC** | RFID eTag + camera AI ANPR đối chiếu chéo; server khớp identity RFID với biển camera đọc ([VETC FAQ](https://vetc.com.vn/hoi-dap-ve-giai-phap-gui-xe-thanh-toan-dien-tu-khong-dung-vetc-n365.html)) | Thiết bị lane tại chỗ | Thanh toán không dừng từ tài khoản VETC; đối chiếu RFID↔ANPR loại bỏ gian lận đổi vé ([eParking](https://eparking.vn/etc-bai-xe/)) | B2B |
| **ePass / Giao thông số** (Viettel) | Claim **99.95%** — đây là độ chính xác đọc thẻ RFID, không phải camera ALPR ([Brixton](https://brixtonvietnam.com.vn/tim-hieu-ve-the-thu-phi-khong-dung-vetc-va-epass)) | Hạ tầng lane | Trừ phí từ tài khoản ePass ([giaothongso.com.vn](https://giaothongso.com.vn/thu-phi-bai-do-xe-khong-su-dung-tien-mat-bang-tai-khoan-epass/)) | B2B |
| **PTH MParking** | "Nhận diện biển số siêu tốc" trên smartphone, không công bố % ([sản phẩm](https://hethonggiuxethongminhpth.com/san-pham/phan-mem-giu-xe-tren-dien-thoai)) | "Zero-hardware": điện thoại Android làm thiết bị cổng (NFC + chụp biển) | Quản lý doanh thu, ảnh vào/ra real-time, claim "chống thất thoát 100%" | Từ **300.000 VNĐ/tháng** |
| MegaParking, VietParking, TB-iParking, SDT Parking | Lane quẹt thẻ + ANPR cho hầm chung cư/văn phòng; không công bố accuracy ([MegaParking](https://megaparking.vn/phan-mem-quan-ly-he-thong-bai-giu-xe-thong-minh/), [VietParking](https://baigiuxethongminh.vn/), [TB-iParking](https://tbvision.com.vn/phan-mem-quan-ly-bai-giu-xe-thong-minh-tb-iparking)) | PC lane + camera IP | Ảnh vào/ra, báo cáo phí, vé tháng | Theo dự án |

### B2. Vendor quốc tế

| Sản phẩm | Claim ALPR | Edge | Dashboard | Giá |
|---|---|---|---|---|
| **Plate Recognizer** + **ParkPow** | Không công bố accuracy %; "works with blurry, low-res, night-time photos"; 90+ quốc gia. **SDK 50–100 ms**, cloud ~200 ms ([site](https://platerecognizer.com/)) | **SDK on-prem chạy Jetson, Raspberry Pi**, Windows/Linux | Log vào/ra + duration, báo cáo occupancy, thực thi policy (giới hạn 3h), tìm theo biển/hãng/model/màu, custom tag + 6 field, alert email/Slack/Teams/SMS, AI xác định hướng xe vào-vs-ra, export CSV/API ([ParkPow](https://platerecognizer.com/parkpow/), [features](https://parkpow.com/features/), [alerts](https://guides.platerecognizer.com/docs/parkpow/user-guide/settings/alerts/)) | Free 2.500 lookup/th; $50/th cho 50k; Stream $35–45/camera/th ([pricing](https://platerecognizer.com/pricing/)) |
| **Rekor Scout / OpenALPR** | "Best-in-class" (không có %); biển + hãng/model/màu/hướng, ~70 quốc gia ([Scout](https://www.openalpr.com/software/scout)) | Agent trên phần cứng thường; camera **Edge Pro** $1.250 ([Edge Pro](https://www.rekor.ai/systems/edge-pro)) | Dashboard web, alert list, lưu 60 ngày (Pro) | $5/th home; Basic **$12/th/camera** ([docs](https://docs.rekor.ai/scout/getting-started/subscriptions-and-licensing)) |
| **Survision** | Không công bố %; thay bằng **Performance Warranty** hợp đồng (tỷ lệ đọc tối thiểu hoặc hoàn tiền); "in as little as 20 ms"; tới 250 km/h ([accuracy](https://survisiongroup.com/post-lets-be-accurate-about-lpr-accuracy), [gen 5](https://survisiongroup.com/post-introducing-the-5th-generation-of-survision-cameras)) | Camera LPR all-in-one xử lý nhúng ([Nanopak](https://survisiongroup.com/post-nanopak)) | Vendor phần cứng, tích hợp vào PARCS | Bán phần cứng |

**Nhận xét về thị trường:** không vendor nghiêm túc nào công bố một con số accuracy đơn lẻ — Survision lập luận rằng claim accuracy một con số là thiếu chặt chẽ và thay bằng cam kết hiệu năng theo hợp đồng. Chuẩn phổ biến ở thị trường Việt Nam là RFID/thẻ kết hợp ANPR đối chiếu chéo để chống gian lận. Về dashboard, ParkPow có tập tính năng phong phú nhất (tag, alert overstay/ngoài giờ, drill-down search, export CSV).

---

## C. Dự án mã nguồn mở

Số sao, giấy phép và ngày push cuối được đối chiếu qua GitHub REST API ngày 2026-07-21.

### C1. Repo Việt Nam

| Repo | Stack | ★ / fork | License | Push cuối | Đánh giá |
|---|---|---|---|---|---|
| [winter2897/Real-time-Auto-LPR-Jetson-Nano](https://github.com/winter2897/Real-time-Auto-License-Plate-Recognition-with-Jetson-Nano) | SSD-MobileNet-v1 detect + SSD OCR (36 class); Colab→ONNX→TensorRT; claim 40 FPS Jetson Nano | 226 / 61 | Không có | 29/07/2021 | Biển VN + công bố dataset VN; đã 5 năm không cập nhật |
| [trungdinh22/License-Plate-Recognition](https://github.com/trungdinh22/License-Plate-Recognition) | YOLOv5 2 giai đoạn (biển → ký tự); PC webcam 15–20 FPS | 100 / 44 | Không có | 13/07/2022 | Hỗ trợ biển VN 1 hàng + 2 hàng; dataset từ Mì AI + winter2897 |
| [mrzaizai2k/VIETNAMESE_LICENSE_PLATE](https://github.com/mrzaizai2k/VIETNAMESE_LICENSE_PLATE) | KNN + OpenCV (không deep learning); biển VN 1 và 2 hàng; use-case bãi giữ xe | 36 / 21 | MIT | 14/11/2025 | Duy nhất trong nhóm VN có giấy phép rõ và còn bảo trì |

**Lưu ý giấy phép:** hai repo VN phổ biến nhất (winter2897, trungdinh22) không khai báo license; theo mặc định luật bản quyền, mã nguồn không được tái sử dụng, chỉ dataset công bố kèm nguồn mới dùng được. Repo có giấy phép hợp lệ: `mrzaizai2k` (MIT), `fast-alpr` (MIT).

### C2. Repo quốc tế

| Repo | Stack | ★ / fork | License | Push cuối | Đánh giá |
|---|---|---|---|---|---|
| [ankandrew/fast-alpr](https://github.com/ankandrew/fast-alpr) | YOLOv9-t detect + CCT OCR (`fast-plate-ocr`), ONNX Runtime (CPU/CUDA/OpenVINO/DirectML/QNN) | **724** / 119 | MIT | **16/03/2026** | ALPR OSS hiện đại, còn bảo trì tích cực; path ONNX CPU phù hợp ARM |
| [RedaAlb/alpr-pipeline](https://github.com/RedaAlb/alpr-pipeline) | YOLO Darknet + ResNet phân loại xe — mã nguồn chính thức của Al-batat 2022 (A2.3) | 9 / 3 | MIT | 31/05/2023 | Hiếm: paper + code + protocol đo khớp nhau |
| [zxllxz2/smart-parking-system](https://github.com/zxllxz2/smart-parking-system) | Frontend React Material Dashboard 2; xem slot, park/checkout, thanh toán | 3 / 3 | MIT | 19/02/2023 | Demo dashboard React, không có ALPR |
| [pratik2374/Automated-Car-parking-system](https://github.com/pratik2374/Automated-Car-parking-system) | Flask + YOLO + Tesseract + ThingSpeak | 1 / 2 | Không có | 21/03/2026 | Giá trị tham khảo thấp |
| [playatanu/smart-car-parking](https://github.com/playatanu/smart-car-parking) | YOLO + OCR, tracking, timestamp vào/ra | 0 / 0 | Không có | 13/02/2025 | Chỉ minh họa ý tưởng session-logging |

**Nhận xét tổng hợp:** các dự án mã nguồn mở khảo sát hoặc là thư viện ALPR thuần (fast-alpr, winter2897), hoặc là ứng dụng bãi xe kiểu demo không có ALPR (zxllxz2). Không dự án nào kết hợp đồng thời ALPR trên edge, backend thực (CSDL, session, tính phí) và dashboard web — đây là một khoảng trống của hệ sinh thái OSS hiện có.

---

## D. Bảng so sánh tính năng các hệ thống khảo sát

Chú thích: ✓ có · ~ một phần · — không có/chưa rõ. Hệ thống Việt Nam liệt kê trước.

| Hệ thống | Occupancy real-time | Log session + ảnh | Tính phí | Báo cáo/thống kê | Alert / chống gian lận | Đa camera | Edge / cloud | Màu biển số |
|---|---|---|---|---|---|---|---|---|
| VETC/ePass (VN, B) | — | ✓ | ✓ (trừ tài khoản) | ✓ | ✓ (**RFID↔ANPR**) | ✓ | Tại chỗ | — |
| PTH MParking (VN, B) | ~ | ✓ (ảnh vào/ra) | ✓ | ✓ (doanh thu) | ~ ("chống thất thoát") | ~ | Cloud/on-prem | — |
| Tran & Bui 2025 (VN, A1.1) | — | — | — | — | — | — | Edge (Pi 4) | — |
| Dang 2024 (VN, A1.2) | — | — | — | — | — | — | N/A | — |
| winter2897 (VN, C1) | — | — | — | — | — | — | Edge (Jetson) | — |
| Pradhan 2025 (A2.1) | ✓ (IR/ô) | ✓ | ✓ (giá động) | ~ | ~ (khớp 88.9%) | ✓ (4 cam) | Edge Pi + server | — |
| Ammar 2023 (A2.2) | — | ~ (log cổng) | — | — | — | ✓ | Edge (Jetson AGX) | — |
| Safran 2024 (A2.4) | ✓ | ~ | — | ✓ (**web dashboard**) | — | ✓ (cam có sẵn) | Server | — |
| Rani 2024 (A2.5) | ~ (chọn block) | ✓ | ✓ (**+QR**) | — | — | — | PC | — |
| Arukonda 2026 (A2.6) | ✓ (phân bổ ô) | ~ (Excel) | — | ~ | ~ (validate định dạng) | — | N/A | — |
| ParkPow (B2) | ✓ | ✓ (ảnh, duration) | ~ (thiên về policy) | ✓ (drill-down) | ✓ (tag, overstay, ngoài giờ) | ✓ | Cả hai | ~ (màu **xe**) |
| Rekor Scout (B2) | — | ✓ | — | ✓ | ✓ | ✓ | Cả hai | ~ (màu **xe**) |
| fast-alpr (C2) | — | — | — | — | — | — | ONNX di động | — |

**Nhận xét tổng hợp:** cột "màu biển số" trống hoàn toàn — kể cả ParkPow và Rekor cũng chỉ nhận diện *màu xe*, không phải *màu biển*; các vendor Việt Nam chống gian lận bằng RFID (phần cứng bổ sung) thay vì tín hiệu thị giác. Bên cạnh đó, không hệ thống khảo sát nào triển khai trọn vẹn ALPR + backend + dashboard trên một thiết bị edge duy nhất, và yêu cầu tuân thủ Luật Bảo vệ dữ liệu cá nhân đối với ảnh biển số hầu như không được đề cập (Ammar 2023 chỉ nêu như hướng phát triển tương lai).

---

## E. Tổng hợp số liệu định lượng từ các nghiên cứu

Nguồn VN đánh dấu **[VN]**. Cột "Evidence" cho biết mức độ tin cậy của số liệu.

| # | Nghiên cứu | Metric | Giá trị | Phần cứng | Evidence | BibTeX |
|---|---|---|---|---|---|---|
| 1 | **[VN]** Tran & Bui 2025 | accuracy nhận dạng | **95.68%** | Raspberry Pi 4B | Thứ cấp | `tran2025vietnamlpr` |
| 2 | **[VN]** Tran & Bui 2025 | thời gian xử lý | **0.478 s/ảnh** | Raspberry Pi 4B | Thứ cấp | `tran2025vietnamlpr` |
| 3 | **[VN]** Le 2023 (xe máy) | mAP detect | **93%** | GPU training | Thứ cấp | `le2023motorcycleplate` |
| 4 | **[VN]** Dang 2024 (bãi trong nhà) | **WER** | **0.014** | N/A | Abstract | `dang2024vietnamcrnn` |
| 5 | Sonnara 2025 | **INT8 vs FP32** | **3.1 → 14.2 FPS (4.6×), mAP 90.6 → 90.2 (−0.4 pp), 5.4 → 4.8 W** | Jetson Nano | Full text | `sonnara2025lightedge` |
| 6 | Ammar 2023 | FPS edge / biển đầy đủ | **17.1 FPS** / **74%** (video) | Jetson Xavier AGX | Full text | `ammar2023multistage` |
| 7 | Ammar 2023 | hiệu ứng voting đa frame | **29% (1 frame) → 69% (35 frame)** | — | Full text | `ammar2023multistage` |
| 8 | Ammar 2023 | hiệu ứng độ phân giải | 1080p **80%** → 720p 72% → 480p **23%** | Jetson AGX | Full text | `ammar2023multistage` |
| 9 | Al-batat 2022 | ký tự tách riêng vs toàn pipeline | **99.68%** vs **90.3%** TB | GTX 1060, 18 FPS | Full text | `albatat2022endtoend` |
| 10 | Pradhan 2025 | khớp biển số hệ thống | **88.9%** (n=100) | Pi 4B + server | Full text | `pradhan2025iotparking` |
| 11 | Pradhan 2025 | accuracy **theo điều kiện** | 95% ngày / 90% tối / 93% góc 45° | Pi 4B | Full text | `pradhan2025iotparking` |
| 12 | Safran 2024 | đa tầng vs single-stage | **96.1% vs 83.9%** | camera giám sát | Abstract | `safran2024multistage` |
| 13 | Rani 2024 | LPR (ảnh hưởng khoảng trắng) | **97.11%** (bỏ space) / **91.91%** (có space) | PC | Abstract | `rani2024ips` |
| 14 | Zhu 2025 | YOLOv8n cải tiến | mAP 90.9 → **94.4%**, tham số 3.1M → **2.1M**, 86 FPS | GPU | Abstract | `zhu2025licenseplate` |
| 15 | Arukonda 2026 | accuracy detect | **98.5%** (latency 50 ms, phần cứng N/A) | N/A | Abstract | `arukonda2026smartparking` |
| 16 | Moussaoui 2024 | detect / ký tự | 99% / 98% (test set 270 ảnh) | N/A | Abstract | `moussaoui2024yolov8ocr` |
| 17 | **[VN]** winter2897 (OSS) | claim FPS edge | 40 FPS (SSD-MobileNet) | Jetson Nano + TensorRT | Claim repo | `winter2897jetsonalpr` |
| 18 | Plate Recognizer (TM) | latency SDK | 50–100 ms/lookup | SDK on-prem | Claim vendor | `platerecognizer2026alpr` |

**Lưu ý phương pháp khi đọc bảng này:**
1. **Dataset khác nhau** (CCPD, Saudi, Ấn Độ, EU/Mỹ/Brazil/Đài Loan, VN) — các con số chỉ mang tính tham khảo, không so sánh head-to-head.
2. **Định nghĩa "accuracy" khác nhau** (cấp ký tự / cấp biển / cấp session / WER). Rani 2024 (#13) cho thấy chỉ đổi cách xử lý khoảng trắng đã lệch 5.2 điểm.
3. **Cỡ test set khác nhau** — Moussaoui (#16, n=270) minh họa rủi ro con số lạc quan trên tập nhỏ.
4. **Không trộn số vendor với số học thuật** — #17, #18 là claim tự công bố, chưa peer-review.

---

## Khoảng trống nghiên cứu

Những khoảng trống rút ra từ toàn bộ khảo sát, cùng một cảnh báo trích dẫn.

- **Phân loại màu biển số làm tín hiệu:** không hệ thống học thuật hay thương mại nào trong khảo sát dùng màu biển số làm tín hiệu chống gian lận hay phân loại xe; các sản phẩm quốc tế chỉ nhận diện màu xe.
- **Triển khai trọn vẹn trên một thiết bị edge:** chưa công trình nào tích hợp đồng thời ALPR, backend (CSDL, session, tính phí) và dashboard trên một thiết bị biên duy nhất; các hệ thống edge hiện có vẫn phụ thuộc server ngoài hoặc cloud.
- **Biển số Việt Nam 2 hàng và tuân thủ dữ liệu cá nhân:** tài liệu về biển xe máy 2 hàng còn ít; yêu cầu tuân thủ Luật Bảo vệ dữ liệu cá nhân đối với ảnh biển số hầu như chưa được xử lý (mới dừng ở mức future work).
- **Công bố số liệu vision-only tại Việt Nam:** không vendor thương mại Việt Nam nào (VETC, ePass, MParking, MegaParking, VietParking, TB-iParking) công bố tỷ lệ nhận dạng biển số dựa trên thị giác — hoặc dùng RFID hoặc giữ kín; số công trình học thuật Việt Nam công bố hệ thống bãi xe đầy đủ (edge + backend + dashboard) kèm protocol tái lập được còn rất hạn chế.

**Cảnh báo trích dẫn:** con số "99.95%" của ePass là độ chính xác đọc thẻ **RFID**, không phải độ chính xác ALPR thị giác; không trích dẫn nhầm thành accuracy vision.
