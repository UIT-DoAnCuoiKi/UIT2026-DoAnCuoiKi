# Báo cáo tuần 7: Ký tự Đ cho OCR, đóng gói ONNX và đo hiệu năng

*(Bản Markdown, khớp nội dung với `w7-onnx.docx` nộp cùng tuần. Sửa nội dung ở file này trước, xuất sang docx sau, để tránh hai bản lệch nhau.)*

## 1. Module OCR: Bổ sung ký tự Đ cho biển xe máy điện

### 1.1 Hiện trạng và nguyên nhân

CRNN đọc biển số hiện tại chỉ nhận diện 36 ký tự (0-9, A-Z). Biển seri MĐ (xe máy điện, quy định thật theo Thông tư 24/2023 và 79/2024/TT-BCA) và TĐ luôn rớt hẳn ký tự Đ khi đọc, không phải đọc nhầm thành ký tự khác.

Lỗi này nguy hiểm hơn lỗi OCR thông thường vì vượt qua cả 2 lớp an toàn hiện có: định dạng vẫn khớp regex do trùng hợp, độ tin cậy vẫn báo cao (97-99%).

Nguyên nhân: 5 chỗ trong code dùng chung 1 regex loại bỏ ký tự ngoài A-Z0-9, vô tình xoá Đ cả ở bước chuẩn bị dữ liệu huấn luyện lẫn ở đường suy luận thật. Khi rà lại dữ liệu, phát hiện dataset topkek_plate_ocr đã có sẵn 169 ảnh thật và 199 ảnh tổng hợp chứa Đ (đa số seri MĐ), nhưng bị đúng bug này làm sai nhãn từ trước tới giờ. Không phải thiếu dữ liệu như giả định ban đầu, mà là dữ liệu có sẵn nhưng bị hỏng nhãn.

### 1.2 Giải pháp và triển khai

- Sửa cả 5 vị trí regex, thêm Đ vào tập ký tự giữ lại.
- Thêm Đ vào CHARSET (36 sang 37 ký tự), NUM_CLASSES tự tăng theo.
- Cập nhật PLATE_PATTERN để chấp nhận Đ trong seri; nới giới hạn `format_display()` lên 5 ký tự phần đầu (phát hiện thêm lúc test: seri MĐ kèm số lô dài 5 ký tự bị hiển thị sai).
- Chạy lại `prepare_ocr_data.py` để tái tạo train/val/test/train_synthetic với nhãn Đ đúng, rồi train lại CRNN (cùng cấu hình cũ: 40 epoch, batch 64, lr 0.001).

### 1.3 Kết quả

So với model chốt trước đó trên cùng `test.csv`:

- Accuracy toàn bộ `test.csv`: 58,9% giảm còn 56,6%.
- Accuracy tập độc lập vn_plate: 87,5% giảm còn 80,2%.

Giảm nhẹ, hợp lý vì model học thêm 1 lớp ký tự mới trong cùng số epoch, không phải dấu hiệu lỗi. Chưa xác định được mức giảm này là do thêm Đ hay chỉ là nhiễu giữa các lần train (chương 4 mục 4.3: hai seed cùng cấu hình lệch nhau 5,2 điểm phần trăm trên vn_plate); cần train thêm seed khác để kiểm chứng, chưa làm.

Riêng 17 biển có Đ trong `test.csv`: 8/17 khớp hoàn toàn cả biển. Soi từng ca sai thì 10/17 model đọc đúng ký tự Đ (7 đúng cả biển, 3 ca chỉ lệch 1 chữ số khác không liên quan đến Đ). 7/17 ca thực sự nhầm Đ thành ký tự khác, chủ yếu D, B, H, C. So với trước đây rớt ký tự này 100% số lần, đây là cải thiện thật dù chưa hoàn hảo.

## 2. Đóng gói mô hình sang ONNX

Xuất 2 model (OCR, phát hiện biển số) sang định dạng ONNX để chạy không cần cài torch, chỉ cần onnxruntime, giúp giảm size, phù hợp thiết bị biên cấu hình thấp như Raspberry Pi 5.

- Kiểm tra `.onnx` cho kết quả khớp `.pt`: OCR khớp 666/666 biển `test.csv`.
- Phát hiện biển số khớp 16/17 ảnh `testimage/` (1 ca lệch do biển rất nhỏ, ở rìa ngưỡng tin cậy).

### 2.1 Đo hiệu năng suy luận trên CPU

Tuần trước mới khẳng định ONNX chạy được mà chưa có số đo. Tuần này đo lại đầy đủ bằng script `src/ml/benchmark_pipeline.py` (đã đưa vào repo để chạy lại và đối chiếu được).

**Cách đo.** Chạy hoàn toàn trên CPU vì mục tiêu triển khai là thiết bị biên không có GPU rời, đo trên GPU sẽ cho con số không suy ra được hiệu năng lúc triển khai thật. Dùng đồng hồ `time.perf_counter()` đo thời gian đồng hồ tường, tức đúng khoảng thời gian người dùng phải chờ. Bỏ 3 lượt chạy đầu để làm nóng, vì lượt đầu phải nạp trọng số từ đĩa và chọn kernel CPU nên chậm bất thường (riêng bước định vị xe: 615 ms lượt đầu so với khoảng 10 ms các lượt sau). Chạy 10 lượt rồi báo cáo **trung vị** kèm min/max thay vì trung bình, để tiến trình nền của máy phát triển không kéo lệch kết quả. Số đo chỉ tính phần tính toán của pipeline: không tính đọc ảnh từ đĩa, không tính truyền HTTP, mã hoá ảnh và ghi cơ sở dữ liệu ở backend (đo riêng đầu-cuối qua API thật cho khoảng 174 ms mỗi lượt, tức phần ngoài suy luận tốn thêm khoảng 100 ms).

**Máy đo.** Intel Core i7-13700K (16 lõi vật lý, 24 luồng logic), 64GB RAM, Windows 11; Python 3.14, onnxruntime 1.28.0 với `CPUExecutionProvider`, PyTorch 2.11.0, OpenCV 5.0.0.

**Ảnh dùng để đo.** Ảnh mẫu commit sẵn trong repo `docs/research/assets/dataset-samples/1_bomaich_detect.png` (1200x600 px, pipeline phát hiện được 12 biển số trên ảnh này), để ai chạy lại cũng cùng điều kiện. Thời gian phụ thuộc số biển phát hiện được vì bước màu biển và OCR chạy lặp cho từng biển, nên khi so sánh bắt buộc phải cùng ảnh.

Kết quả đo từng model ONNX chạy riêng lẻ (đầu vào tensor ngẫu nhiên đúng kích thước, chỉ đo chi phí tính toán của đồ thị):

| Model | Kích thước ONNX | 1 luồng | 4 luồng |
|---|---:|---:|---:|
| Phát hiện biển số (YOLOv8n) | 12,2 MB | 65,58 ms | 19,53 ms |
| OCR biển số (CRNN) | 1,7 MB | 1,14 ms | 0,48 ms |
| Phân loại loại xe (ResNet18) | 44,7 MB | 24,57 ms | 6,84 ms |
| Phân loại loại xe (MobileNetV3-Small) | 6,1 MB | 1,54 ms | 0,90 ms |
| Phân loại kiểu dáng xe (ResNet18) | 44,7 MB | 25,21 ms | 6,94 ms |

Lưu ý khi đọc bảng trên: không cộng các dòng lại thành thời gian của cả pipeline. Chạy riêng thì mỗi model được dùng trọn số luồng cấu hình, còn trong pipeline chúng chạy nối tiếp, chia nhau tài nguyên và có thêm chi phí tiền xử lý ảnh.

Thời gian từng bước khi chạy trong pipeline thật:

| Bước | 1 luồng (mặc định) | 4 luồng |
|---|---:|---:|
| Phát hiện biển số (ONNX) | 68,8 ms (40%) | 29,3 ms |
| Màu biển và OCR (12 biển) | 35,2 ms (21%) | 22,7 ms |
| Phân loại kiểu dáng (ONNX) | 26,5 ms (16%) | 10,1 ms |
| Phân loại loại xe (ONNX) | 24,8 ms (15%) | 8,9 ms |
| Định vị và cắt vùng xe (YOLO) | 11,2 ms (7%) | 11,9 ms |
| Tiền xử lý ảnh cho classifier | 2,6 ms | 3,1 ms |
| Chuyển màu BGR sang RGB | 1,2 ms | 1,4 ms |
| **Toàn pipeline (trung vị)** | **146,8 ms** | **76,2 ms** |

### 2.2 Hai lỗi hiệu năng phát hiện được khi đo

Đo thử cũng lộ ra 2 lỗi thật, cộng lại làm pipeline chậm hơn khoảng 6 lần so với mức đáng lẽ đạt được:

- **Model bị nạp lại từ đĩa mỗi khung hình.** Hàm cắt vùng xe gọi lệnh nạp model ngay bên trong hàm xử lý từng ảnh, nên mỗi lượt đều đọc lại trọng số từ đĩa: 135 ms mỗi lượt so với 12,6 ms nếu nạp một lần rồi dùng lại, tức chậm hơn gần 11 lần. Đã sửa bằng cách cache model theo tiến trình.
- **Tranh chấp luồng CPU giữa các model.** Pipeline nạp cùng lúc 4-5 model nhỏ chạy nối tiếp trên 1 ảnh, mà mỗi model theo mặc định lại tự phân luồng theo toàn bộ số lõi của máy. Đo được pipeline tốn khoảng 21 giây CPU-time cho 1 ảnh trong chưa tới 1 giây đồng hồ tường, tức đang toả ra hàng chục luồng chỉ để làm vài phép nhân ma trận nhỏ, chi phí đồng bộ hoá luồng vượt xa thời gian tính toán thật. Đã sửa bằng cách giới hạn số luồng mỗi model qua biến môi trường `ML_INTRAOP_THREADS`, mặc định 1 luồng cho an toàn trên mọi máy kể cả Raspberry Pi.

Cách phát hiện lỗi thứ hai đáng ghi lại vì không nhìn ra được nếu chỉ đo thời gian đồng hồ: so tỉ số giữa `time.process_time()` (tổng CPU-time của mọi luồng) và `time.perf_counter()` (thời gian đồng hồ tường). Tỉ số bằng khoảng 1 nghĩa là chạy gần như đơn luồng; ở đây đo được tỉ số khoảng 24 trên máy 24 luồng logic, tức mọi lõi đều bị huy động cho một khối lượng tính toán rất nhỏ.

Kết quả sau khi sửa cả 2: từ 780-900 ms mỗi ảnh và dao động rất mạnh (340 đến 1200 ms) xuống còn 146,8 ms ổn định (dao động dưới 10 ms) ở cấu hình mặc định, và 76,2 ms nếu đặt 4 luồng trên máy nhiều lõi. Bước tốn thời gian nhất hiện là phát hiện biển số (40% tổng thời gian), nên nếu cần tối ưu tiếp thì ưu tiên bước đó trước.

### 2.3 Đo trên Raspberry Pi 5

Máy đo là Raspberry Pi 5 Model B 16GB, chạy Debian 13 trên thẻ microSD, nguồn khai báo tối đa 3000 mA, có quạt tản nhiệt (thông tin ghi trong `src/ml/experiments/pi5/may_do.txt`). Cấu hình model giống backend đang chạy trên Pi: 4 luồng, định vị xe bằng `yolov8n.pt`, kiểu dáng bằng MobileNetV3-Small ONNX.

Nhóm đo hai lần riêng, dùng chung một bộ ảnh:

| Lần đo | Mục đích | Script | Log gốc |
|---|---|---|---|
| A: gọi `run()` trực tiếp | So hai model kiểu dáng, đo điện năng | `run_pi_anh_that.sh`, `benchmark_anh_that.py`, `summarize_pi_anh_that.py` | `src/ml/experiments/pi5_anh_that/` |
| B: gọi API của backend | Độ trễ đầu-cuối | `run_pi_do_tre_api.sh`, `do_tre_api.py` | `src/ml/experiments/pi5_do_tre_api/` |

Các bảng dưới đây tính lại được từ log bằng notebook `src/ml/notebooks/benchmark-raspberry-pi5.ipynb`.

**Cách đo.**

- Ảnh: 50 ảnh camera cổng thật (25 ô tô, 25 xe máy), chọn ngẫu nhiên với seed 2026 từ tập val của A1, danh sách ở `src/ml/data/anh_cong_benchmark.txt`.
- Lần A: nạp hết ảnh vào bộ nhớ, làm nóng 3 ảnh, rồi gọi `OnnxAlprPipeline.run()` 5 vòng trên mỗi ảnh, bấm giờ bằng `time.perf_counter()`. Mỗi ảnh lấy trung vị 5 vòng, sau đó tính trung vị và phân vị 90 trên 50 ảnh. Không tính thời gian đọc ảnh.
- Lần B: chạy một backend riêng ở cổng 8001 với cùng biến model như service thật, trỏ vào bản sao cơ sở dữ liệu; backend chính tạm dừng để không tranh CPU. `do_tre_api.py` gọi `POST /captures/infer` 3 vòng trên mỗi ảnh, bấm giờ từ lúc gửi tới lúc nhận phản hồi. Phản hồi có trường `timings_ms.tong` là tổng thời gian các bước pipeline có bấm giờ (đổi màu, phát hiện biển, màu biển, OCR, định vị xe, loại xe, kiểu dáng). Phần ngoài suy luận tính trên cùng một request, `t_ngoài = t_client - timings_ms.tong`, gồm HTTP, giải mã ảnh, lưu ảnh, ghi cơ sở dữ liệu và đoạn code không bấm giờ giữa các bước. Client và backend chạy cùng máy nên chưa gồm độ trễ mạng LAN.
- Điện năng: chip quản lý nguồn (PMIC) của Pi 5 có ADC đo dòng và áp trên từng nhánh nguồn. `pi_power_monitor.py` đọc `vcgencmd pmic_read_adc` mỗi giây và tính `P = Σ V_k × I_k`, chỉ cộng những nhánh có cả dòng và áp. Mốc thời gian của mỗi cấu hình do `benchmark_anh_that.py` ghi và chỉ bao vòng gọi `run()`, nên `E mỗi lượt = P trung bình trong mốc × độ dài mốc / số lượt`. Con số này là cận dưới của điện năng lấy từ ổ cắm vì không tính hao phí củ sạc và thiết bị USB.
- Nhiệt độ và hạ xung: cùng script ghi nhiệt độ SoC, xung CPU và `vcgencmd get_throttled` mỗi giây. Bit 0 đến 3 của `get_throttled` lần lượt báo sụt áp, đang giới hạn xung, đang hạ xung và chạm ngưỡng nhiệt mềm. Trước mỗi cấu hình của lần A và trước lần B, script chờ tới khi phần nguyên nhiệt độ SoC không quá 58°C, tối đa 5 phút.
- Kết quả nhận dạng: so chuỗi biển, loại xe và kiểu dáng từng ảnh của lần A với cùng cấu hình chạy trên máy dev (`src/ml/experiments/anh_that_dev/`).

**Kết quả lần B: độ trễ đầu-cuối qua API.** 150 lượt (50 ảnh × 3 vòng), mỗi ảnh lấy trung vị 3 vòng. Nguồn: `pi5_do_tre_api/do_tre_api.log`.

| | Trung vị | Phân vị 90 | Lớn nhất |
|---|---:|---:|---:|
| Đầu-cuối phía client | 463,4 ms | 487,9 ms | 497,2 ms |
| Các bước suy luận (`timings_ms.tong`) | 445,8 ms | 465,8 ms | 475,3 ms |
| Ngoài suy luận, cùng request | 17,5 ms | 22,1 ms | 29,1 ms |

Cả 150 lượt trả HTTP 200 và đều có loại xe, biển số. Lượt đầu tiên sau khi khởi động backend mất 4,8 giây vì backend nạp model ở lượt này (`do_tre_api_luot_dau.txt`). Lần đo kéo dài 77 giây, nhiệt độ SoC từ 57,3°C lên 77,7°C, không mẫu nào bật bit 0 đến 3.

**Kết quả lần A: 50 ảnh, 5 vòng mỗi ảnh.** Nguồn: `pi5_anh_that/tong_hop.csv`, `pt_mnv3.csv`, `pt_resnet.csv`.

| | MobileNetV3-Small | ResNet18 |
|---|---:|---:|
| `run()`, trung vị 50 ảnh | 464,4 ms | 463,0 ms |
| `run()`, phân vị 90 | 487,7 ms | 539,1 ms |
| Trung vị 18 ảnh có qua bước kiểu dáng | 482,0 ms | 536,4 ms |
| Trung vị 32 ảnh không qua bước kiểu dáng | 461,4 ms | 459,5 ms |
| Điện năng mỗi lượt | 3,12 J | 3,25 J |
| Điện năng tăng thêm so với lúc nghỉ (1,55 W) | 2,39 J | 2,49 J |
| Kết quả nhận dạng trùng máy dev | 50/50 ảnh | 50/50 ảnh |
| Thời gian đo liên tục | 118,1 s | 122,3 s |
| Mẫu bật bit 0 đến 2 | 0/114 | 0/118 |
| Mẫu bật bit 3 (ngưỡng nhiệt mềm) | 3/114 | 13/118 |
| Xung CPU thấp nhất trong mốc | 2400 MHz | 2400 MHz |

Bước kiểu dáng chỉ chạy khi model loại xe trả `car` và bước định vị tìm được vùng xe, tức 18/50 ảnh, trùng nhau ở hai cấu hình. So từng ảnh trong 18 ảnh này, ResNet18 chậm hơn MobileNetV3-Small từ 30,6 đến 68,5 ms, trung vị 51,3 ms. Ở 32 ảnh còn lại, hai lần chạy lệch nhau từ -18,7 đến 12,5 ms, là mức dao động giữa hai lần chạy. Phần lớn ảnh không qua bước kiểu dáng nên trung vị trên cả 50 ảnh của hai cấu hình gần bằng nhau, còn phân vị 90 thì khác rõ.

Về nhiệt độ, sau 1 đến 2 phút tải liên tục SoC lên 82 đến 83°C và bật bit 3 ở một số mẫu (bảng trên). Không mẫu nào bật bit 1 hoặc 2, xung CPU giữ 2400 MHz suốt cả hai mốc, và trung vị theo từng vòng trên 50 ảnh không tăng dần (467 đến 469 ms với MobileNetV3-Small, 463 đến 472 ms với ResNet18), nên nhóm vẫn dùng số của lần A. Trước MobileNetV3-Small, SoC đã nguội xuống 57,9°C trong lần nghỉ đầu; trước ResNet18, script chờ hết 5 phút mà nhiệt độ thấp nhất chỉ 59,5°C, chưa đạt điều kiện 58°C.

**Bộ nhớ.** Tiến trình chạy `benchmark_pipeline.py` với 4 luồng dùng tối đa 705 đến 766 MiB (`ru_maxrss`, script `run_pi_ram.sh`, log `pi5/ram_*.log`). Tiến trình này nạp pipeline hai lần và nạp thêm các model đo riêng nên đây là cận trên. Cấu hình `.pt` + MobileNetV3-Small đang dùng chưa được đo riêng. Máy có 16GB RAM nên còn dư nhiều.

**Hạn chế.**

- Mỗi cấu hình chỉ chạy liên tục khoảng 2 phút ở lần A và 77 giây ở lần B. Chưa đo tải liên tục lâu hơn nên chưa biết khi đó CPU có bị hạ xung không.
- Điện năng đọc từ PMIC là cận dưới, chưa đối chiếu với đồng hồ đo USB-C ở ổ cắm.
- Độ trễ chưa gồm mạng LAN và thời gian lấy khung hình từ camera.

**Kết luận.**

- Đạt mốc đề cương: đầu-cuối qua API 463,4 ms mỗi lượt, phân vị 90 là 487,9 ms, nhanh hơn mốc 2 giây khoảng 4 lần. Lượt đầu sau khi khởi động backend mất 4,8 giây vì nạp model; nạp sẵn model lúc khởi động sẽ tránh được độ trễ này.
- Bước kiểu dáng dùng MobileNetV3-Small ONNX: accuracy ngang ResNet18 (0,9007 so với 0,8997), bản ONNX khớp `.pt` trên 987/987 ảnh test, và trên Pi mỗi ảnh có qua bước này nhanh hơn trung vị 51,3 ms.
- Kết quả nhận dạng trên Pi trùng máy dev ở cả 50 ảnh, cho cả hai cấu hình.
- Điện năng 3,12 J mỗi lượt xe với cấu hình đang dùng.
- 4 luồng và `.pt` cho bước định vị xe chọn theo lần đo ma trận trước đó trên ảnh mẫu `1_bomaich_detect.png` (`pi5/tong_hop.csv`): 4 luồng nhanh nhất ở cả ba cấu hình, bản `.onnx` chậm hơn `.pt` (1.067,4 so với 813,9 ms ở 1 luồng, 535,0 so với 495,3 ms ở 4 luồng).

## 3. Tiến hành xây dựng module Backend và Dashboard

### 3.1 Kiến trúc

FastAPI cộng SQLAlchemy 2.0 cộng Alembic cộng PostgreSQL, đóng gói bằng Podman (3 service: backend, database, worker tự xoá dữ liệu theo hạn lưu trữ). Nhận kết quả pipeline AI từ thiết bị biên, quản lý phiên vào ra, khớp biển, tính phí, thống kê. Bảo mật: mã hoá tầng cột, JWT, audit log, đúng cam kết đề cương về bảo vệ dữ liệu cá nhân.

### 3.2 Việc đã làm trong tuần

- Phân quyền 3 cấp root/manager/staff, giới hạn route và giao diện theo vai trò; ẩn KPI thống kê khỏi màn hình vận hành tại cổng vì lý do riêng tư.
- Quản lý danh mục nhóm xe: thêm, sửa, xoá có ràng buộc không xoá nhóm đang được tham chiếu, chặn tạo bảng giá cho nhóm xe không tồn tại.
- Giao diện vận hành tại cổng: chọn camera, xem trước, chụp ảnh trực tiếp qua webcam, gửi khung hình lên API suy luận và nhận kết quả theo thời gian thực qua WebSocket, phân theo hướng vào/ra.
- Xuất báo cáo thống kê ra CSV.

## 4. Kết quả đạt được

- OCR đọc đúng ký tự Đ cho biển xe máy điện, không còn rớt hẳn ký tự này như trước.
- Toàn bộ pipeline nhận diện (phát hiện biển số, OCR) chạy được bằng ONNX, không cần torch lúc suy luận, và weights đồng bộ tự động qua git giữa các máy.
- Đo được hiệu năng suy luận thật trên CPU bằng script tái lập được: toàn pipeline 146,8 ms mỗi ảnh ở cấu hình mặc định và 76,2 ms trên máy nhiều lõi, sau khi sửa 2 lỗi hiệu năng phát hiện trong lúc đo (nạp lại model mỗi khung hình, và tranh chấp luồng CPU giữa các model).
- Đo trên Raspberry Pi 5 thật với 50 ảnh camera cổng: đầu-cuối qua API 463,4 ms mỗi lượt (phân vị 90 là 487,9 ms), nhanh hơn mốc 2 giây của đề cương khoảng 4 lần; điện năng 3,12 J mỗi lượt xe; kết quả nhận dạng trùng máy dev ở cả 50 ảnh. Bước kiểu dáng chuyển sang MobileNetV3-Small ONNX (khớp `.pt` 987/987 ảnh), nhanh hơn ResNet18 trung vị 51,3 ms trên mỗi ảnh có qua bước này.
