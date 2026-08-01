# Chương 1: Tổng quan đề tài

## 1.1 Nghiên cứu và hệ thống liên quan

Trước khi thiết kế pipeline, nhóm đã khảo sát các hệ thống ALPR (Automatic License Plate Recognition) và quản lý bãi xe hiện có, cả trong nước lẫn quốc tế, để làm cơ sở tham chiếu về kiến trúc, số liệu độ chính xác/tốc độ, và xác định khoảng trống mà đề tài có thể đóng góp. Phân công khảo sát:

- **Nhật:** các dự án mã nguồn mở và giải pháp thương mại (trong nước lẫn quốc tế), cùng các bộ dữ liệu/benchmark tham chiếu — ghi tại `docs/research/khao-sat-he-thong-alpr.md`.
- **Đức:** các công trình học thuật (hệ thống bãi xe hoàn chỉnh, có tích hợp session/tính phí/dashboard) và bảng số liệu định lượng đối chiếu giữa các nghiên cứu — ghi tại `docs/research/2026-07-19-similar-parking-systems.md`.

### 1.1.1 Nghiên cứu học thuật trong nước

**LPR Việt Nam trên thiết bị nhúng**
- Tác giả: Vanha Tran, Thiloan Bui
- Năm: 2025
- Link: [doi.org/10.1007/978-981-96-0695-5_19](https://link.springer.com/chapter/10.1007/978-981-96-0695-5_19) (Springer, MIWAI 2024)
- Tóm tắt: SSD-MobileNetV2 phát hiện vùng biển, YOLOv8-nano nhận dạng ký tự theo hướng OCR-as-detection (không dùng engine OCR truyền thống), chạy trên Raspberry Pi 4 Model B + Pi Camera V2. Đạt độ chính xác nhận dạng trung bình 95,68%, thời gian xử lý 0,478 giây/ảnh — hiếm hoi trong số các nguồn khảo sát có đo trực tiếp trên phần cứng edge cùng lớp với Raspberry Pi 5 mà đề tài hướng tới. Chưa công bố cỡ tập test, chưa phân biệt kết quả giữa biển 1 hàng và 2 hàng.

**Nhận dạng biển số xe Việt Nam bằng CRNN cải tiến kèm attention**
- Tác giả: L. T. A. Dang, V. D. Ngoc, P. C. L. T. Vu, N. N. Truong, P. T. Bao, T. D. Trinh
- Năm: 2024
- Link: [doi.org/10.1007/s13177-024-00402-7](https://link.springer.com/article/10.1007/s13177-024-00402-7)
- Tóm tắt: YOLO phát hiện xe → WPOD-NET trích xuất vùng biển (xử lý tốt biển bị nghiêng góc) → CRNN cải tiến huấn luyện đồng thời với CTC loss và cơ chế attention để đọc ký tự. Dữ liệu huấn luyện tự thu tại một bãi đỗ xe trong nhà ở Việt Nam — đúng bối cảnh use-case của đề tài. Đạt Word Error Rate 0,014 trong tác vụ OCR; công trình mới dừng ở khâu nhận dạng, chưa mở rộng sang quản lý phiên gửi xe hay tính phí.

**Phát hiện và nhận dạng biển số xe máy Việt Nam bằng YOLOv8 ba tầng**
- Tác giả: D. H. Le, D. Mazumder, L.-D. Quach, S. Banerjee, V.-D. Nguyen
- Năm: 2023
- Link: [doi.org/10.1007/978-981-99-8296-7_5](https://link.springer.com/chapter/10.1007/978-981-99-8296-7_5) (Springer, FDSE 2023)
- Tóm tắt: Kiến trúc YOLOv8 ba tầng — phát hiện xe máy, sau đó phát hiện biển số bên trong vùng xe máy đã phát hiện, cuối cùng nhận dạng ký tự. Đạt mAP 93% sau 300 epoch, hướng tới ứng dụng phạt nguội vi phạm tốc độ. Chưa công bố số liệu tốc độ xử lý.

**Nhận dạng biển số đa góc nhìn (PTIT)**
- Tác giả: D. Tran-Anh, K. L. Tran, H.-N. Vu
- Năm: 2023
- Link: [arXiv:2309.12972](https://arxiv.org/abs/2309.12972)
- Tóm tắt: Kết hợp đặc trưng corner-point/diện tích từ ba góc nhìn khác nhau trước khi nhận dạng bằng CnOCR, nhằm tăng độ bền của mô hình theo góc chụp. Xây dựng bộ dữ liệu PTITPlates tự thu tại Học viện Công nghệ Bưu chính Viễn thông. Bài báo không công bố số liệu định lượng cụ thể nên chưa dùng được làm baseline so sánh.

**UIT MAPR 2018 — Vietnamese Bike License Plate Recognition Challenge**
- Tác giả: Ban tổ chức MAPR 2018 (UIT)
- Năm: 2018
- Link: [mapr.uit.edu.vn](https://mapr.uit.edu.vn/2018/vietnamese-bike-license-plate-recognition) (đường dẫn tải dataset hiện không còn truy cập được)
- Tóm tắt: Cuộc thi và bộ dữ liệu 3.000 ảnh xe máy chụp tại bãi giữ xe khách sạn ở Việt Nam (2.000 train/1.000 test), gồm phát hiện biển và nhận dạng ký tự. Có giá trị dẫn nguồn lịch sử cho nghiên cứu biển số xe máy tại UIT, dù dữ liệu gốc không còn tải được.

### 1.1.2 Nghiên cứu học thuật quốc tế

**Hệ thống bãi xe IoT tích hợp ALPR và quản lý thanh toán**
- Tác giả: G. Pradhan, M. R. Prusty, V. S. Negi, S. Chinara (Vellore Institute of Technology & NIT Rourkela, Ấn Độ)
- Năm: 2025
- Link: [doi.org/10.1038/s41598-025-86441-w](https://www.nature.com/articles/s41598-025-86441-w) (full text mở tại [PMC11742719](https://pmc.ncbi.nlm.nih.gov/articles/PMC11742719/))
- Tóm tắt: Hệ thống hoàn chỉnh nhất về mặt tích hợp trong số các nguồn khảo sát được — một Raspberry Pi 4 Model B quản lý 4 camera, kết hợp cảm biến IR + ESP32 gắn tại mỗi ô đỗ, chạy YOLO phát hiện biển và Tesseract OCR, có quản lý phiên gửi xe, tính phí động theo giờ cao/thấp điểm, và theo dõi tình trạng chỗ trống. Độ chính xác nhận dạng biển số được báo cáo tách theo điều kiện:
  - Tỷ lệ khớp biển số tổng thể: 88,9% (trên 100 trường hợp thử nghiệm)
  - Ban ngày: 95%
  - Ánh sáng yếu: 90%
  - Góc chụp 45°: 93%

**Hệ thống nhận dạng xe và biển số đa tầng, suy luận thời gian thực trên biên**
- Tác giả: A. Ammar, A. Koubaa, W. Boulila, B. Benjdira, Y. Alhabashi (Prince Sultan University, Ả Rập Xê Út)
- Năm: 2023
- Link: [doi.org/10.3390/s23042120](https://doi.org/10.3390/s23042120) (full text mở tại [PMC9966104](https://pmc.ncbi.nlm.nih.gov/articles/PMC9966104/))
- Tóm tắt: Triển khai thực tế tại cổng bãi xe của Đại học Prince Sultan, dùng pipeline năm tầng (YOLOv4 phát hiện xe/biển, phân loại đời xe, nhận dạng ký tự, DeepSORT theo dõi đa khung hình có voting, tối ưu bằng TensorRT) chạy trên Jetson Xavier AGX ở tốc độ 17,1 FPS. Hai phát hiện định lượng đáng chú ý:
  - Voting đa khung hình: độ chính xác nhận dạng biển tăng từ 29% (một khung hình) lên 69% khi voting qua tối đa 35 khung hình liên tiếp
  - Độ phân giải camera: độ chính xác giảm mạnh từ 80% (1080p) xuống 23% (480p) — ngưỡng tối thiểu nên từ 720p trở lên

**Hệ thống ALPR đầu-cuối, có mã nguồn mở**
- Tác giả: R. Al-batat, A. Angelopoulou, S. Premkumar, J. Hemanth, E. Kapetanios
- Năm: 2022
- Link: [doi.org/10.3390/s22239477](https://doi.org/10.3390/s22239477) · mã nguồn: [github.com/RedaAlb/alpr-pipeline](https://github.com/RedaAlb/alpr-pipeline) (MIT license)
- Tóm tắt: Công trình duy nhất trong khảo sát vừa có toàn văn mở, vừa có mã nguồn giấy phép MIT, đánh giá trên 5 bộ dữ liệu công khai thuộc nhiều khu vực (Mỹ, EU, Đài Loan, Brazil) với protocol đo minh bạch (IoU riêng cho từng tầng phát hiện/nhận dạng). Đạt độ chính xác toàn pipeline 90,3% ở cấp ký tự, phân loại loại xe (ResNet50) đạt 98,22%.

**Phát hiện và nhận dạng biển số đa tầng bằng YOLOv8 kèm dashboard web**
- Tác giả: M. Safran, A. Alajmi, S. Alfarhood
- Năm: 2024
- Link: [doi.org/10.1155/2024/4917097](https://doi.org/10.1155/2024/4917097)
- Tóm tắt: YOLOv5 phát hiện biển → YOLOv8 phát hiện ký tự → CNN tự thiết kế phân loại ký tự, tận dụng camera giám sát có sẵn trong bãi thay vì lắp phần cứng mới. Cho bằng chứng định lượng rõ ràng về lợi ích kiến trúc đa tầng so với single-stage (96,1% so với 83,9%). Tích hợp dashboard web trực quan hóa occupancy và luồng xe theo thời gian thực.

**Light-Edge — lượng tử hóa INT8 cho nhận dạng biển số trên thiết bị biên**
- Tác giả: F. Sonnara, H. Chihaoui, F. Filali
- Năm: 2025
- Link: [doi.org/10.1007/s11554-025-01738-3](https://doi.org/10.1007/s11554-025-01738-3) (CC-BY 4.0, full text mở)
- Tóm tắt: Kiến trúc Light-Edge dùng chung backbone ResNet-18 + FPN cho cả phát hiện và nhận dạng, benchmark trên Jetson Nano với bộ dữ liệu CCPD. Lượng tử hóa INT8 giúp tăng tốc độ xử lý 4,6 lần (từ 3,1 lên 14,2 FPS) trong khi chỉ đánh đổi 0,4 điểm phần trăm mAP, nhờ kỹ thuật giữ lớp đầu và lớp cuối của mạng ở độ chính xác FP16 — kết quả trực tiếp liên quan đến kế hoạch lượng tử hóa INT8 cho Raspberry Pi 5 của đề tài.

### 1.1.3 Sản phẩm thương mại

**VNPT AI Camera**
- Đơn vị: VNPT
- Link: [vnpt.com.vn](https://vnpt.com.vn/doanh-nghiep/san-pham-dich-vu/gia%CC%89i-pha%CC%81p-vnpt-ai-camera/)
- Tóm tắt: Kết hợp nhận diện khuôn mặt và biển số, xử lý trên cloud hoặc edge tùy gói, có thêm tính năng giám sát giao thông (vượt đèn đỏ, sai làn, dừng đỗ trái phép). Không công bố số liệu độ chính xác của riêng khâu nhận dạng biển số.

**PTH MParking**
- Đơn vị: PTH
- Link: [hethonggiuxethongminhpth.com](https://hethonggiuxethongminhpth.com/san-pham/phan-mem-giu-xe-tren-dien-thoai)
- Tóm tắt: Ứng dụng smartphone làm thiết bị cổng (NFC + chụp biển), không cần lắp thêm phần cứng chuyên dụng ("zero-hardware"), giá từ 300.000 VNĐ/tháng. Không công bố % độ chính xác.

**Plate Recognizer + ParkPow**
- Đơn vị: Plate Recognizer
- Link: [platerecognizer.com](https://platerecognizer.com/)
- Tóm tắt: SDK on-prem chạy được trên Jetson, Raspberry Pi, Windows/Linux, độ trễ 50–100 ms/ảnh (SDK) hoặc ~200 ms (cloud), hỗ trợ hơn 90 quốc gia. Dashboard ParkPow có tập tính năng phong phú (log vào/ra, alert quá giờ, tìm theo biển/hãng/model/màu, export CSV/API). Không công bố % độ chính xác.

**Rekor Scout / OpenALPR**
- Đơn vị: Rekor
- Link: [openalpr.com/software/scout](https://www.openalpr.com/software/scout)
- Tóm tắt: Hỗ trợ khoảng 70 quốc gia, camera chuyên dụng Edge Pro giá 1.250 USD, gói Basic từ 12 USD/tháng/camera. Dashboard web có alert list, lưu log 60 ngày (gói Pro). Không công bố % độ chính xác.

### 1.1.4 Dự án mã nguồn mở

**VIETNAMESE_LICENSE_PLATE**
- Tác giả: mrzaizai2k
- Link: [github.com/mrzaizai2k/VIETNAMESE_LICENSE_PLATE](https://github.com/mrzaizai2k/VIETNAMESE_LICENSE_PLATE)
- Tóm tắt: Dùng KNN kết hợp OpenCV (không deep learning) để xử lý cả biển 1 hàng và 2 hàng của Việt Nam, hướng thẳng tới use-case bãi giữ xe. Giấy phép MIT, vẫn còn được bảo trì — hiếm hoi trong nhóm dự án Việt Nam khảo sát được có giấy phép rõ ràng.

**fast-alpr**
- Tác giả: ankandrew
- Link: [github.com/ankandrew/fast-alpr](https://github.com/ankandrew/fast-alpr)
- Tóm tắt: Tách rời detector (YOLOv9-tiny) và OCR (`fast-plate-ocr`) thành hai mô hình độc lập, chạy qua ONNX Runtime trên nhiều nền tảng (CPU/CUDA/OpenVINO/DirectML/QNN). Giấy phép MIT, đang được bảo trì tích cực (724 sao GitHub). Kiến trúc tách interface detector/OCR tương đồng với hướng đề tài đã chọn, phù hợp tham khảo khi triển khai trên phần cứng ARM như Raspberry Pi.

### 1.1.5 Khoảng trống nghiên cứu và định vị đề tài

Từ toàn bộ khảo sát, có thể rút ra ba khoảng trống chính mà đề tài hướng tới lấp đầy:

1. **Chưa hệ thống nào tích hợp trọn vẹn trên một thiết bị biên duy nhất.** Kể cả các hệ thống học thuật hoàn chỉnh nhất như Pradhan (2025) hay Ammar (2023) cũng chưa gộp đồng thời phát hiện/nhận dạng, backend (cơ sở dữ liệu, quản lý phiên, tính phí) và dashboard vào một thiết bị biên — vẫn phụ thuộc server ngoài hoặc cloud.
2. **Chưa hệ thống nào dùng màu nền biển số làm tín hiệu.** Không hệ thống nào trong khảo sát — cả học thuật lẫn thương mại — sử dụng màu nền biển số (trắng/vàng/xanh) để phân loại; các sản phẩm quốc tế như ParkPow hay Rekor chỉ nhận diện màu xe, không phải màu biển.

Đây chính là các điểm khác biệt mà hệ thống đề xuất trong đồ án hướng tới giải quyết: phát hiện, nhận dạng, phân loại màu biển, quản lý phiên/tính phí và dashboard.

*(Danh sách BibTeX đầy đủ, kèm DOI và ghi chú evidence-level cho từng nguồn, có sẵn tại `docs/research/refs.bib` và `docs/research/2026-07-19-similar-parking-systems.md`.)*
