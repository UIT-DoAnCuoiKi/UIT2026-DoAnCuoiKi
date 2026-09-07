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

Giảm nhẹ, hợp lý vì model học thêm 1 lớp ký tự mới trong cùng số epoch, không phải dấu hiệu lỗi. Chưa xác định được mức giảm này là do thêm Đ hay chỉ là nhiễu giữa các lần train (chương 4 mục 4.3 đã ghi nhận nhiễu này có thể trên 10 điểm phần trăm); cần train thêm seed khác để kiểm chứng, chưa làm.

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

### 2.3 Việc còn tồn: đo trên Raspberry Pi 5

Toàn bộ số liệu ở trên đo trên máy phát triển x86, **chưa phải thiết bị triển khai thật**, nên chưa trả lời được câu hỏi quan trọng nhất là hệ thống có chạy đủ nhanh trên Pi hay không. Dự kiến làm ở tuần sau, dùng đúng script `benchmark_pipeline.py` này để hai bên số liệu so sánh được với nhau. Ba điểm cần lưu ý khi đo trên Pi:

- **Số luồng tối ưu nhiều khả năng khác hẳn.** Pi chỉ có 4 lõi, trong khi máy dev có 24 luồng logic. Giá trị mặc định `ML_INTRAOP_THREADS=1` được chọn chính vì lý do này, nhưng vẫn phải đo lại để xác nhận thay vì suy đoán.
- **Có thể không cài torch trên Pi.** Bước định vị xe mặc định chạy qua ultralytics nên kéo theo torch, khá nặng với Pi. Nếu muốn chạy hoàn toàn không cần torch thì trỏ `ML_COARSE_WEIGHTS` sang bản `.onnx` để dùng nhánh onnxruntime thuần (đã làm sẵn, xem chương 5 mục 5.6). Lúc đó cần đo cả 2 nhánh để biết trên ARM nhánh nào thật sự nhanh hơn: trên x86 nhánh `.pt` nhanh hơn (147,3 ms so với 218,5 ms cùng điều kiện), nhưng ARM không có các tối ưu CPU như x86 nên kết quả có thể ngược lại.
- **Đo cả nhiệt độ và xung nhịp.** Pi bị giảm xung khi nóng, nên số đo lần đầu chạy nguội có thể đẹp hơn thực tế lúc chạy liên tục ở trạm cổng.

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
