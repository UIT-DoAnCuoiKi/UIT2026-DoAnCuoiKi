# Chương 5: Phân loại phương tiện

Chương này trình bày module phân loại loại xe (Nhật, Tuần 5, bổ sung sau tích hợp pipeline). Kiến trúc gồm 3 bước:

1. **Loại xe** (ô tô/xe máy/xe tải): model tự huấn luyện, chạy thẳng trên cả khung hình, thay cho việc dùng nhãn lớp COCO của YOLO pretrained như bản đầu tiên (xem 5.1-5.4).
2. **Định vị xe**: model YOLO pretrained (COCO), không huấn luyện thêm, chỉ để tìm và cắt vùng xe phục vụ bước 3, không tham gia quyết định loại xe.
3. **Kiểu dáng xe con** (chỉ chạy khi bước 1 ra "ô tô" và bước 2 cắt được vùng xe): model tự huấn luyện, 3 lớp: `Sedan`, `Gầm cao`, `Xe tải`.

*(Bước 2 là phần bổ sung sau khi kết thúc Tuần 5. Bản đầu tiên dùng thẳng nhãn lớp COCO của YOLO pretrained cho cả bước 1 và bước "loại xe" gộp làm một; sau khi phát hiện cách này sai nhiều trên ảnh cận cảnh kiểu camera cổng, nhóm huấn luyện riêng một model cho bước này và tách nó ra khỏi bước định vị. Các số liệu "kiểm thử trên ảnh thật" ở mục 5.4 đo dưới cách làm cũ được giữ nguyên làm bằng chứng lịch sử, có ghi chú kèm theo.)*

**Lưu ý về phạm vi so với đề cương (đã cập nhật):** đề cương ghi "huấn luyện đủ 4 lớp (ô tô, xe máy, xe tải, xe buýt), đánh giá sâu 2 lớp chính". Bản đầu tiên (Tuần 5) không huấn luyện riêng, dùng thẳng model YOLO pretrained cho cả 4 lớp vì có bằng chứng thực nghiệm (mục 5.5) rằng model tự huấn luyện lúc đó kém hơn hẳn model pretrained trên ảnh thật. Sau khi làm lại dữ liệu (mục 5.1), nhóm đã huấn luyện được model riêng, có accuracy/F1 đo được, cho 3/4 lớp: `car`, `motorbike`, `truck`. Lớp còn thiếu là `bus`: dữ liệu hiện có không đủ ảnh xe khách cận cảnh đúng góc camera cổng để huấn luyện. Phương án tạm ban đầu là mượn nhãn `bus` của YOLO pretrained, nhưng đo lại cho thấy nhãn đó sai cả 2/2 lần trên tập test nên đã bỏ (mục 5.4); xe khách hiện bị xếp vào một trong 3 lớp có sẵn, chờ nhân viên sửa tay ở màn Trạm cổng. Khoảng cách với yêu cầu đề cương vì vậy đã thu hẹp từ 4/4 lớp xuống còn 1/4 lớp, nhưng vẫn cần trao đổi với giảng viên hướng dẫn về việc lớp `bus` còn thiếu có chấp nhận được không.

## 5.1 Dữ liệu

### Dữ liệu cho bước loại xe (car/motorbike/truck)

Nguồn: `data/raw/kaggle_vn_plate_segment` (cùng bộ dữ liệu module phát hiện biển của Đức đang dùng), chia sẵn theo 5 tiền tố tên file với nội dung rất khác nhau, đã xem tay xác nhận:

| Tiền tố | Số ảnh | Nội dung |
|---|---:|---|
| `carlong_*` | 989 | Ô tô cận cảnh kiểu camera barrier/gờ giảm tốc, thuần 1 loại (xem tay ~15 ảnh, 15/15 ô tô) |
| `greenpack_*` | 1.747 | Xe máy cận cảnh kiểu CCTV cổng, thuần 1 loại (xem tay ~15 ảnh, 15/15 xe máy) |
| `Dieu_*`/`Hung_*` | 925 | Ảnh phố hỗn hợp nhiều loại xe, hậu cảnh lộn xộn |
| `Tgmt_*` | 917 | Cắt cực sát, chỉ thấy biển số và ca-lăng, không dùng được cho phân loại loại xe |

**Lần huấn luyện đầu tiên mắc lỗi "học tắt" (shortcut learning).** Mỗi lớp lấy từ đúng 1 nguồn ảnh: `car` lấy 350 ảnh `carlong_`, `motorbike` lấy 350 ảnh `greenpack_`, `truck` lấy 73 ảnh `Dieu_`/`Hung_` (xem cách lọc bên dưới). Kết quả trên tập test riêng đạt 100% ở cả 2 kiến trúc, nhưng khi kiểm tra lại trên ảnh `Dieu_`/`Hung_` thật ngoài tập train (ảnh phố, không phải camera cổng), model chỉ đúng 1/13, mọi ảnh còn lại đều bị đoán thành `truck`. Nguyên nhân: `truck` là lớp DUY NHẤT có ảnh phong cách đường phố lúc đó, nên model học "đặc điểm phong cách ảnh/góc camera" thay vì hình dáng xe thật. Đây là bài học quan trọng về phương pháp: accuracy cao trên tập test nội bộ không chứng minh được gì nếu tập test đó chia sẻ cùng thiên lệch nguồn dữ liệu với tập train (xem thêm mục 5.5).

**Cách sửa: trộn phong cách ảnh cho từng lớp**, để mỗi lớp đều có cả ảnh cận cảnh cổng lẫn ảnh đường phố, buộc model phải học hình dáng xe thay vì học nguồn ảnh:

- `car`: giữ 350 ảnh `carlong_`, bổ sung 92 ảnh đường phố. Quét YOLOv8n pretrained trên 925 ảnh `Dieu_`/`Hung_` ra 216 ứng viên nhãn "car", lấy mẫu 128 ứng viên rồi xem tay từng ảnh (tiêu chí: ô tô là chủ thể chính, không phải chỉ lấp ló hậu cảnh); 92/128 đạt.
- `motorbike`: giữ 350 ảnh `greenpack_`, bổ sung 128 ảnh đường phố. Quét ra 481 ứng viên nhãn "motorcycle", lấy mẫu 128 rồi xem tay; 128/128 đạt (không có dương tính giả nào, vì xe máy có hình dáng đặc trưng hơn hẳn xe tải/van dễ nhầm với ô tô).
- `truck`: dataset gốc không có thư mục riêng cho xe tải, toàn bộ 73 ảnh đều lấy từ `Dieu_`/`Hung_`. Quét ra 151 ứng viên nhãn "truck", xem tay TỪNG ảnh trong cả 151 (không chỉ lấy mẫu) vì độ tin cậy của detector không đáng tin để lọc tự động: dương tính giả rải đều ở mọi mức điểm, kể cả điểm cao (một ảnh Toyota Camry vẫn ra nhãn "truck" với độ tin cậy 0,79); 73/151 đạt.

Chia tập theo tỉ lệ chung 70/15/15 (không cố định số lượng theo lớp, vì lớp `truck` ít ảnh hơn hẳn 2 lớp còn lại) và seed cố định để tái lập được:

| Lớp | Train | Valid | Test | Tổng |
|---|---:|---:|---:|---:|
| `car` | 309 | 66 | 67 | 442 |
| `motorbike` | 335 | 72 | 71 | 478 |
| `truck` | 51 | 11 | 11 | 73 |

Tổng 993 ảnh. Lớp `truck` mỏng hơn nhiều (73 ảnh so với 442-478), xử lý mất cân bằng bằng trọng số lớp trong hàm loss, giống cách đã làm với bước kiểu dáng xe con.

### Dữ liệu cho bước kiểu dáng xe con

B5 (Vehicle Body Style Dataset, Roboflow, CC BY 4.0, 10.000 ảnh: train 7.014 / valid 1.999 / test 987, 12 kiểu dáng gốc) dùng làm nguồn duy nhất cho bước phân loại kiểu dáng xe con.

**Gộp 12 kiểu dáng gốc còn 3 nhóm thực dụng hơn**, phù hợp nhu cầu vận hành bãi xe (sedan/gầm cao/xe tải), thay vì 12 kiểu dáng chi tiết không có ý nghĩa vận hành rõ ràng:

| Nhóm mới | Kiểu dáng gốc B5 gộp vào |
|---|---|
| `Sedan` | Sedan, Fastback, Hatchback, Wagon, Convertible, Hardtop Convertible, Sports |
| `Gầm cao` | SUV, Crossover, MPV, Minibus |
| `Xe tải` | Pickup Truck |

Ảnh cắt theo bbox gốc (thêm biên 10%), giữ nguyên split train/valid/test của Roboflow. Số ảnh sau khi gộp:

| Lớp | Train | Valid | Test |
|---|---:|---:|---:|
| Sedan | 4.102 | 1.166 | 569 |
| Gầm cao | 2.325 | 670 | 334 |
| Xe tải | 587 | 163 | 84 |

Tổng 10.000 ảnh.

![Phân bố lớp theo split](../figures/vehicle_style_class_distribution.png)

Lớp `Xe tải` ít nhất nhưng vẫn có 587 ảnh train, đủ để huấn luyện ổn định. Xử lý mất cân bằng lớp bằng trọng số trong hàm loss.

Dữ liệu B5 còn hạn chế domain gap: ảnh train là ảnh dealer/showroom, một phần bối cảnh Trung Quốc, không phải ảnh camera giám sát Việt Nam. Bàn kỹ hơn ở mục 5.5.

## 5.2 Kiến trúc mô hình

**Bước loại xe:** cùng công thức kiến trúc với bước kiểu dáng, so sánh 2 kiến trúc fine-tune từ trọng số ImageNet, thay lớp cuối cho 3 lớp `car`/`motorbike`/`truck`:
- **ResNet18**: 11.178.051 tham số.
- **MobileNetV3-Small**: 1.520.931 tham số.

Ảnh vào là **cả khung hình**, resize 224×224, chuẩn hóa theo thống kê ImageNet, augmentation giống hệt bước kiểu dáng (random-resized-crop, lật ngang, xoay ±10°, color jitter). Dùng cả khung hình chứ không dùng vùng xe đã cắt là có chủ đích: dữ liệu huấn luyện của bước này là ảnh camera cổng nguyên khung (`prepare_vehicle_type_dataset.py` chép thẳng ảnh gốc, không cắt), nên đưa ảnh nguyên vào lúc suy luận mới đúng phân phối lúc train. Bản đầu tiên đưa vùng crop của YOLO vào và điều đó gây ra một lỗi nghiêm trọng ở mức pipeline, phân tích ở mục 5.4.

**Bước định vị xe:** một model YOLO pretrained trên COCO, không huấn luyện thêm, dùng để tìm và cắt vùng xe cho bước kiểu dáng và để trả toạ độ khung xe. Trong thử nghiệm này nhóm dùng cụ thể YOLOv8n, nhưng thiết kế cho phép thay bằng phiên bản YOLO khác (YOLOv9, YOLO26...) mà không cần đổi logic pipeline. Với 1 ảnh đầu vào, lấy box xe có diện tích lớn nhất, crop kèm biên 10%. Nhãn lớp COCO của bước này (`car`/`motorcycle`/`bus`/`truck`, id 2/3/5/7) từng được dùng thẳng làm kết quả loại xe ở bản đầu tiên, **nay không còn được dùng làm nhãn nữa**, kể cả cho lớp `bus` (lý do đo được ở mục 5.4).

**Bước kiểu dáng (chỉ chạy khi bước loại xe ra "car"):** so sánh 2 kiến trúc, fine-tune từ trọng số ImageNet, thay lớp cuối cho 3 lớp:
- **ResNet18**: 11.178.051 tham số.
- **MobileNetV3-Small**: 1.520.931 tham số, nhẹ hơn ResNet18 khoảng 7,3 lần.

Ảnh vào 224×224, chuẩn hóa theo thống kê ImageNet. Augmentation: random-resized-crop (scale 0,8-1,0), lật ngang, xoay ±10°, color jitter.

## 5.3 Huấn luyện

Huấn luyện local trên GPU NVIDIA RTX 4070, không dùng Colab để tránh giới hạn phiên free tier. Cấu hình chung cho cả bước loại xe và bước kiểu dáng: Adam, learning rate 1e-4, batch size 32, 15 epoch, `CrossEntropyLoss` có trọng số lớp.

| Model | Thời gian train (loại xe) | Thời gian train (kiểu dáng) |
|---|---:|---:|
| ResNet18 | 2,66 phút | 6,09 phút |
| MobileNetV3-Small | 2,62 phút | 6,09 phút |

Bước loại xe nhanh hơn hẳn vì dữ liệu nhỏ hơn nhiều (993 ảnh so với 10.000 ảnh).

![Tài nguyên hệ thống trong suốt quá trình train](../figures/vehicle_style_resource_usage.png)

Theo dõi tài nguyên thật trong lúc train bước kiểu dáng (lấy mẫu mỗi 5 giây, `src/ml/monitor_resources.py`, 153 mẫu): CPU trung bình 11,5% (đỉnh 31,3%), GPU trung bình 25,6% (đỉnh 98%), VRAM ổn định quanh 3,5GB/12GB. Mô hình nhỏ nên không tận dụng hết GPU; bước loại xe dùng cùng cấu hình nên có đặc điểm tương tự.

![Đường train loss và validation accuracy theo epoch](../figures/vehicle_style_loss_curves.png)

Cả 2 kiến trúc hội tụ nhanh và ổn định. Bài toán 3 lớp dễ hơn hẳn bài toán 12 lớp đã thử trước đó: accuracy epoch 1 đã trên 0,80, so với khoảng 0,4-0,6 ở bản 12 lớp. Khoảng cách giữa ResNet18 và MobileNetV3-Small cũng thu hẹp đáng kể so với bài toán 12 lớp.

## 5.4 Kết quả

### Bước loại xe

Đánh giá trên tập test (149 ảnh, không dùng khi train hay chọn tham số), sau khi đã sửa lỗi học tắt ở mục 5.1:

| Model | Accuracy | F1-macro | Params | ONNX | CPU inference |
|---|---:|---:|---:|---:|---:|
| ResNet18 | 0,9866 | 0,9619 | 11.178.051 | 44,70 MB | 8,19 ms/ảnh |
| MobileNetV3-Small | 0,9799 | 0,9571 | 1.520.931 | 6,09 MB | 4,22 ms/ảnh |

Ma trận nhầm lẫn (thứ tự lớp `car`/`motorbike`/`truck`):

- ResNet18: `[[67,0,0],[0,71,0],[1,1,9]]`, tức `car` và `motorbike` đúng tuyệt đối (67/67, 71/71), `truck` đúng 9/11, 1 ảnh bị đoán thành `car` và 1 ảnh thành `motorbike`.
- MobileNetV3-Small: `[[67,0,0],[1,70,0],[1,1,9]]`, `car` đúng tuyệt đối, `motorbike` đúng 70/71 (1 ảnh bị đoán thành `car`), `truck` đúng 9/11 như ResNet18.

`truck` là lớp yếu nhất ở cả 2 model, hợp lý vì đây cũng là lớp ít ảnh nhất (chỉ 11 ảnh test); nhầm lẫn còn lại phân tán đều sang `car` và `motorbike` chứ không lệch hẳn về một hướng, không cho thấy dấu hiệu học tắt như bản đầu tiên.

### Kiểm tra ngoài phân phối (OOD) sau khi sửa dữ liệu

Để xác nhận lỗi học tắt ở mục 5.1 đã thực sự được sửa chứ không chỉ "che" bằng cách thêm dữ liệu tương tự tập test, nhóm dựng một bộ kiểm tra cố định gồm 12 ảnh thật (`Dieu_`/`Hung_`) có nhãn đúng đã biết, **không nằm trong bất kỳ tập train/valid/test nào** (`src/ml/sanity_check_vehicle_type_ood.py`, giữ lại vĩnh viễn làm bài test hồi quy, không chỉ chạy một lần rồi bỏ):

| Model | Đúng / Tổng | Accuracy OOD |
|---|---:|---:|
| ResNet18 | 12/12 | 100% |
| MobileNetV3-Small | 11/12 | 92% |

So với 1/13 của lần huấn luyện đầu tiên (mục 5.1), đây là bằng chứng trực tiếp cho thấy việc trộn phong cách ảnh đã giải quyết đúng nguyên nhân gốc, không phải một chỉnh sửa tình cờ. Bài học phương pháp rút ra: khi nghi ngờ model học tắt, cách kiểm chứng đáng tin là một tập OOD nhỏ nhưng chắc chắn tách biệt nguồn với tập train, không phải chia lại tập test lớn hơn từ cùng nguồn dữ liệu.

### Đo lại ở mức PIPELINE, không chỉ ở mức model

Accuracy 98,66% ở trên là của riêng model, đo bằng cách nạp thẳng ảnh vào model. Khi ghép vào pipeline thật, kết quả người dùng nhận được có thể khác hẳn, và ở đây đúng là đã khác hẳn. Bản ghép đầu tiên đặt bước định vị YOLO làm điều kiện: *nếu YOLO không tìm được xe thì bỏ qua, không phân loại*. Chạy lại chính tập test loại xe qua pipeline đầy đủ cho thấy hậu quả:

| Lớp | Số ảnh | YOLO tìm được xe | **Không ra kết quả** |
|---|---:|---:|---:|
| car | 67 | 30 | **37 (55%)** |
| motorbike | 71 | 23 | **48 (68%)** |
| truck | 11 | 11 | 0 |
| **Tổng** | **149** | 64 | **85 (57%)** |

57% số ảnh mà model phân loại đúng tới 98,66% lại không hề được đưa tới model, chỉ vì YOLOv8n pretrained COCO (không huấn luyện lại) không nhận ra có xe trong ảnh cận cảnh kiểu camera cổng. Ví dụ cụ thể `greenpack_1343.png` (xe máy chụp từ phía sau): YOLO đoán ra `person` 62,5% và `handbag` 18,4%, không có lớp xe nào; trong khi model loại xe chạy thẳng trên đúng ảnh đó cho `motorbike` 99,9%.

Sửa bằng cách bỏ hẳn sự phụ thuộc này: model loại xe chạy trên cả khung hình, đúng như dữ liệu lúc train (mục 5.2), YOLO chỉ còn phục vụ bước kiểu dáng. Điều kiện an toàn duy nhất còn giữ là phải có bằng chứng trong khung hình thật sự có xe (YOLO thấy xe **hoặc** module biển số đọc được biển), tránh khung hình trống bị ép về một trong 3 lớp. Kết quả sau khi sửa:

| | Trước khi sửa | Sau khi sửa |
|---|---:|---:|
| Ảnh có ra được loại xe | 64 / 149 (43%) | **149 / 149 (100%)** |
| Đúng end-to-end | 62 / 149 (41,6%) | **147 / 149 (98,7%)** |
| Xe máy bị bỏ sót | 48 / 71 (68%) | **0** |

98,7% end-to-end giờ khớp đúng accuracy 98,66% của bản thân model, tức pipeline không còn làm mất chất lượng của model nữa; 2 ảnh sai còn lại chính là 2 ảnh xe tải đã thấy trong ma trận nhầm lẫn ở trên.

**Nhân đây cũng bỏ luôn việc dùng nhãn `bus` của COCO làm phương án dự phòng.** Model tự huấn luyện chưa có lớp xe khách nên bản đầu giữ lại nhãn `bus` của YOLO cho trường hợp đó. Đo trên tập test: YOLO gọi `bus` đúng 2 lần và **sai cả 2** (đều là ô tô con), một lần ở mức tin cậy 0,781 nên đặt ngưỡng lọc cũng không cứu được. Giữ lại nhánh này chỉ làm hỏng 2 ca vốn đã đúng, nên bỏ. Xe khách vẫn là hạn chế đã biết (mục 5.5), xử lý bằng thao tác sửa tay của nhân viên ở màn Trạm cổng.

Bài học phương pháp, tương tự bài học về học tắt ở trên nhưng ở một tầng khác: **accuracy của model không phải accuracy mà người dùng nhận được**. Cần đo lại ở mức pipeline đầy đủ, vì một thành phần khác trong chuỗi (ở đây là bước định vị không được huấn luyện) có thể chặn mất phần lớn đầu vào trước khi model kịp chạy.

### Kiểm thử trên ảnh thật (đo dưới pipeline Tuần 5, trước khi có bước loại xe riêng)

*(Bảng này giữ nguyên làm bằng chứng lịch sử cho quyết định "dùng model pretrained cho loại thô" nêu ở mục 5.5. Cột "Loại thô" là nhãn COCO thô của YOLO pretrained lúc đó, chưa qua bước loại xe tự huấn luyện; pipeline hiện tại ghi đè nhãn này bằng model ở mục 5.4 cho 3 lớp car/motorbike/truck.)*

Để kiểm chứng thực tế, không chỉ tin vào accuracy trên tập test nội bộ, nhóm chạy pipeline đầy đủ (model YOLO cho loại thô, ResNet18 cho kiểu dáng) trên 8 ảnh thật thu thập ngoài dataset, gồm ảnh camera cổng bãi xe thật và ảnh xe phổ biến ở Việt Nam:

| Ảnh | Thực tế | Loại thô | Kiểu dáng | Đúng? |
|---|---|---|---|---|
| Xe máy tại bãi gửi xe (camera trần) | Xe máy | motorcycle (62,9%) | (không áp dụng) | ✓ |
| Xe máy tại cổng có kiosk vé | Xe máy | motorcycle (70,0%) | (không áp dụng) | ✓ |
| Hyundai Santa Fe (SUV) | SUV | car (78,4%) | Gầm cao (99,8%) | ✓✓ |
| Xe máy tại cổng, có nhân viên | Xe máy | motorcycle (53,7%) | (không áp dụng) | ✓ |
| VinFast (crossover điện), camera cổng chúc xuống | Crossover | car (33,2%) | Gầm cao (69,2%) | ✓✓ |
| Mitsubishi Xpander (crossover/MPV), camera cổng chúc xuống | Crossover/MPV | car (35,6%) | Sedan (53,1%, Gầm cao 36,8%) | Đúng loại thô, sai sát biên ở kiểu dáng |
| Toyota Yaris (sedan), camera cổng chúc xuống | Sedan | không phát hiện được | (không áp dụng) | ✗ |
| Xe tải chở hàng thật (biển 29H) | Xe tải | truck (31,5%) | (không áp dụng) | ✓ |

7/8 đúng ở bước loại thô. Trong 3 ảnh được đưa tiếp sang bước kiểu dáng, 2/3 đúng rõ ràng, 1/3 (Xpander) sai nhưng biên độ sát (53% so với 37%), hợp lý vì Xpander là dáng lai sedan/MPV. Điểm yếu còn lại: ảnh chụp từ camera cổng chúc xuống gắt (3 ảnh cuối) làm độ tin cậy giảm (33-36% so với 60-95% ở ảnh chụp ngang tầm mắt), và 1 trường hợp bị bỏ sót hoàn toàn. Model YOLO pretrained quen ảnh chụp ngang tầm mắt (theo phân phối COCO), chưa quen góc camera cổng bãi xe thật.

![So sánh ResNet18 vs MobileNetV3-Small](../figures/vehicle_style_comparison.png)

![Ma trận nhầm lẫn trên tập test](../figures/vehicle_style_confusion_matrices.png)

### Kết quả bước kiểu dáng

Đánh giá trên tập test (987 ảnh, không dùng khi train hay chọn tham số):

| Model | Accuracy | F1-macro | Params | ONNX | CPU inference |
|---|---:|---:|---:|---:|---:|
| ResNet18 | 0,8997 | 0,9012 | 11.178.051 | 44,70 MB | 8,57 ms/ảnh |
| MobileNetV3-Small | 0,9007 | 0,9069 | 1.520.931 | 6,09 MB | 4,82 ms/ảnh |

*(CPU inference đo trên máy train, không phải Raspberry Pi 5. Số Pi 5 thật để dành Tuần 7-8.)*

So với bài toán 12 lớp đã thử trước đó, accuracy cải thiện rõ rệt (ResNet18 từ 0,768 lên 0,900, MobileNetV3-Small từ 0,701 lên 0,901). Với chỉ 3 lớp, MobileNetV3-Small gần như ngang bằng ResNet18 về accuracy dù nhẹ hơn 7,3 lần, khác hẳn khoảng cách lớn ở bài toán 12 lớp.

Ma trận nhầm lẫn cho thấy `Sedan` và `Xe tải` được phân loại tốt (93,1-96,4% đúng tùy model). Nhầm lẫn tập trung ở `Gầm cao`, là lớp yếu nhất ở cả 2 model (79,6% với ResNet18, 83,2% với MobileNetV3-Small), chủ yếu bị đoán nhầm thành `Sedan` (18,3% và 15,0% số ảnh tương ứng). Điều này hợp lý vì crossover cỡ nhỏ đôi khi có dáng gần sedan, ranh giới giữa 2 nhóm này vốn không tuyệt đối rõ ràng kể cả với người quan sát.

## 5.5 Thảo luận

**Accuracy trên tập test nội bộ không đảm bảo hiệu năng thật.** Đây là lý do chính khiến nhóm ban đầu chọn dùng model YOLO pretrained cho bước loại thô thay vì tự huấn luyện: lần huấn luyện đầu (mục 5.1) đạt accuracy rất cao trên tập test riêng của nó nhưng hiệu năng giảm mạnh (1/13) khi gặp ảnh thật ngoài phân phối train, vì mỗi lớp lúc đó chỉ lấy từ đúng 1 nguồn ảnh. Bài học rút ra không phải "model tự huấn luyện luôn kém hơn pretrained", mà là: độ đa dạng nguồn ảnh trong tập train quan trọng hơn số lượng ảnh hay accuracy đo được trên một tập test cùng nguồn. Sau khi trộn nguồn ảnh đúng cách (mục 5.1), model tự huấn luyện đạt 100% và 92% trên bộ kiểm tra OOD, tốt hơn hẳn phương án dùng thẳng nhãn COCO (7/8 đúng loại thô, không có số liệu accuracy chính thức vì không phải model được đánh giá có kiểm soát).

**Về việc dùng model pretrained thay vì huấn luyện riêng theo đề cương (đã cập nhật):** quyết định ban đầu dùng model pretrained cho cả 4 lớp có căn cứ thực nghiệm tại thời điểm đó, nhưng khác chữ "huấn luyện" của đề cương. Sau khi sửa dữ liệu và huấn luyện lại, nhóm đã có model riêng cho 3/4 lớp (`car`, `motorbike`, `truck`), thu hẹp đáng kể khoảng cách này. Lớp `bus` vẫn chưa có model riêng vì dữ liệu hiện có không đủ ảnh xe khách cận cảnh đúng góc camera cổng; nếu cần tuân thủ đúng chữ đề cương cho lớp này, hướng khắc phục là thu thập thêm dữ liệu xe khách theo đúng góc camera cổng bãi xe rồi lặp lại đúng quy trình đã dùng cho 3 lớp kia. Cần trao đổi với giảng viên hướng dẫn xem mức độ hoàn thành này (3/4 lớp có accuracy đo được, 1/4 lớp dùng tạm pretrained) có được coi là đạt yêu cầu hay không.

**Hạn chế còn lại của bước định vị xe:** YOLO pretrained COCO bỏ sót xe trên 57% ảnh camera cổng trong tập test (mục 5.4), vì nó chưa từng được huấn luyện với góc chụp này. Sau khi tách bước loại xe ra khỏi bước định vị, hậu quả đã thu hẹp đáng kể: loại xe và biển số vẫn cho kết quả đầy đủ, chỉ còn 2 thứ phụ thuộc bước định vị là **toạ độ khung xe** (`vehicle_box`, chỉ dùng để hiển thị) và **bước kiểu dáng** (bắt buộc cần vùng crop vì model đó huấn luyện trên ảnh đã cắt). Nghĩa là với 57% ảnh nói trên, hệ thống vẫn ra loại xe và biển số đúng, chỉ không có thêm thông tin kiểu dáng xe con. Muốn khắc phục nốt thì cần dữ liệu đúng góc camera cổng để fine-tune riêng bước định vị, hoặc huấn luyện lại bước kiểu dáng trên ảnh nguyên khung như đã làm với bước loại xe.

**Hạn chế của bước kiểu dáng:** vẫn train hoàn toàn trên B5, ảnh dealer/showroom, một phần bối cảnh Trung Quốc. Số liệu 90% trên tập test B5 đo đúng khả năng phân biệt kiểu dáng trong cùng phong cách ảnh với tập train, chưa chứng minh được trên ảnh camera giám sát Việt Nam thật. Ảnh test thật ở mục 5.4 cho thấy tín hiệu tích cực (2/3 đúng, 1/3 sát biên) nhưng cỡ mẫu quá nhỏ để kết luận chắc chắn.

**Hướng tiếp theo:** thu thập dữ liệu xe khách đúng góc camera cổng để huấn luyện nốt lớp `bus`; tìm hoặc thu thập dữ liệu đúng góc camera cổng bãi xe cho bước định vị (YOLO); đo lại thời gian inference thật trên Raspberry Pi 5, có thể thêm INT8 quantization, chọn model triển khai (cả bước loại xe lẫn kiểu dáng) dựa trên số đo thật.

## 5.6 Hướng dẫn tích hợp vào pipeline

Mục này mô tả pipeline THẬT đang chạy trong backend (`app/services/ml_inference.py`) và edge worker (`src/edge/worker.py`), nguồn sự thật dùng chung nằm ở `src/ml/pipeline/onnx_pipeline.py`. `src/ml/predict_vehicle.py` vẫn còn nhưng chỉ là bản CLI tham khảo cho 1 ảnh, không phải code chạy thật của hệ thống.

### Các file cần dùng

| File | Vai trò |
|---|---|
| `src/ml/weights/yolov8n.pt` | Model YOLO pretrained, chỉ dùng để định vị + cắt vùng xe cho bước kiểu dáng (nhãn lớp của nó không dùng làm loại xe), backend mặc định (tự tải về lần chạy đầu, không commit vào git) |
| `src/ml/weights/yolov8n.onnx` | Cùng model, xuất ONNX, backend thay thế không cần torch/ultralytics (đổi qua biến môi trường `ML_COARSE_WEIGHTS`) |
| `src/ml/weights/vehicle-type-resnet18.onnx` / `.pt` | Model loại xe, bản ResNet18 (44,7 MB), mặc định dùng trong pipeline |
| `src/ml/weights/vehicle-type-mobilenet_v3_small.onnx` / `.pt` | Model loại xe, bản MobileNetV3-Small (6,1 MB) |
| `src/ml/data/vehicle-type-classes.json` | Thứ tự lớp của model loại xe (`["car","motorbike","truck"]`) |
| `src/ml/weights/vehicle-style-resnet18.pt` / `.onnx` | Model kiểu dáng, bản ResNet18 (44,8 MB), mặc định dùng trong pipeline |
| `src/ml/weights/vehicle-style-mobilenet_v3_small.pt` | Model kiểu dáng, bản MobileNetV3-Small (6,2 MB) |
| `src/ml/data/vehicle-style-classes.json` | Thứ tự lớp của model kiểu dáng |
| `src/ml/training/classifier.py` | Chứa `build_model()` và `build_transforms()`, dùng chung cho cả model loại xe và kiểu dáng |
| `src/ml/pipeline/onnx_pipeline.py` | `OnnxAlprPipeline`, pipeline thật chạy đủ 4 model (định vị, loại xe, kiểu dáng, cộng module biển số của Đức) |
| `src/ml/predict_vehicle.py` | Bản CLI tham khảo, chạy được bước định vị + kiểu dáng cho 1 ảnh (không có bước loại xe) |
| `src/ml/benchmark_pipeline.py` | Script đo hiệu năng, sinh ra mọi số trong mục "Hiệu năng đo được" bên dưới; chạy lại được để đối chiếu trên máy khác |

### Luồng xử lý (đúng như code thật)

1. Chạy module biển số trước (phát hiện biển, màu biển, OCR). Ngoài kết quả biển số, bước này còn cho một tín hiệu dùng ở bước 3: đọc được biển nghĩa là chắc chắn trong khung hình có xe.
2. Đưa ảnh vào model YOLO (`predict_vehicle.detect_vehicle_crop`), lọc các box thuộc 4 lớp `car`(2) / `motorbike`(3, đổi tên từ `motorcycle` của COCO, xem ghi chú bên dưới) / `bus`(5) / `truck`(7), chọn box lớn nhất, crop kèm biên 10% mỗi chiều. Chỉ dùng để lấy `vehicle_box` và ảnh crop cho bước 4; **nhãn lớp COCO của bước này bị bỏ đi, không dùng làm loại xe**.
3. Nếu có bằng chứng trong khung hình có xe (bước 2 tìm được box **hoặc** bước 1 đọc được biển), đưa **cả khung hình** qua model loại xe tự huấn luyện để lấy nhãn `car`/`motorbike`/`truck`. Không có bằng chứng nào thì để `vehicle_type` là rỗng thay vì đoán bừa.
4. Nếu nhãn ở bước 3 là `car` **và** bước 2 cắt được vùng xe, đưa ảnh đã crop (không phải cả khung hình) qua model kiểu dáng để lấy `Sedan` / `Gầm cao` / `Xe tải`.

### Sáu điểm dễ sai khi tích hợp

**Đừng để một model KHÔNG được huấn luyện quyết định thay cho model đã huấn luyện.** Đây là lỗi nặng nhất gặp phải, mất 57% số ca (mục 5.4). Bản đầu tiên đặt bước định vị YOLO pretrained làm điều kiện chạy của model loại xe; YOLO trượt là cả chuỗi phía sau im lặng trả rỗng, dù model loại xe hoàn toàn xử lý được ảnh đó. Nguyên tắc rút ra khi ghép nhiều model: xác định rõ model nào là thành phần đã được đánh giá có số liệu, và không để một thành phần chưa đánh giá đứng chặn đầu vào của nó. Nếu buộc phải có điều kiện, hãy chọn điều kiện dựa trên bằng chứng độc lập (ở đây là "đọc được biển số") thay vì dựa vào chính thành phần yếu.

**Đưa đúng loại ảnh mà model được huấn luyện.** Model loại xe huấn luyện trên ảnh nguyên khung nên phải nạp cả khung hình; model kiểu dáng huấn luyện trên ảnh cắt theo bbox (kèm biên 10%) nên phải nạp vùng crop. Đưa nhầm loại ảnh vào thì code vẫn chạy, vẫn ra kết quả, chỉ là độ chính xác tụt mà không có dấu hiệu báo lỗi nào.

**Thứ tự lớp đầu ra theo bảng chữ cái.** `ImageFolder` của torchvision sắp xếp tên thư mục theo bảng chữ cái khi huấn luyện, nên thứ tự lớp của model kiểu dáng là `['GamCao', 'Sedan', 'XeTai']`, không phải thứ tự "Sedan, Gầm cao, Xe tải" thường dùng khi trình bày; model loại xe cũng vậy, thứ tự thật là `['car', 'motorbike', 'truck']`. Cách an toàn nhất khi viết code tích hợp là đọc trực tiếp danh sách lớp từ file lớp đi kèm (`vehicle-type-classes.json`/`vehicle-style-classes.json`, hoặc `ckpt["class_names"]` nếu dùng checkpoint `.pt`) thay vì hard-code.

**Tiền xử lý phải khớp đúng lúc huấn luyện:** resize cạnh ngắn về 256, center-crop 224×224, chuẩn hóa theo mean/std của ImageNet, dùng chung cho cả model loại xe và kiểu dáng. Dùng lại `build_transforms(train=False)` trong `classifier.py` là cách an toàn nhất. Sai bước này sẽ làm độ chính xác giảm mạnh mà vẫn chạy bình thường.

**Đặt lại tên nhãn từ `motorcycle` (COCO) thành `motorbike`.** Bản đầu tiên giữ nguyên tên lớp COCO (`motorcycle`) khi trả kết quả; bảng nhóm phí của backend (`app/services/vehicle_groups.py`) và nhãn hiển thị của frontend chỉ nhận `motorbike`. Lệch tên khiến MỌI xe máy không được gán nhóm phí tự động cho tới khi phát hiện và sửa (`group_for("motorcycle")` luôn trả `None`). Model loại xe tự huấn luyện xuất đúng `motorbike` ngay từ đầu nên việc tích hợp nó vào pipeline vô tình sửa luôn lỗi này; nếu chỉ dùng bước định vị YOLO đơn thuần thì vẫn phải tự đổi tên nhãn.

**Nạp model một lần, không nạp lại mỗi khung hình.** Bước định vị dùng ultralytics (`YOLO(weights)`), nếu gọi hàm nạp model bên trong hàm xử lý từng khung hình thì mỗi lần gọi sẽ đọc lại trọng số từ đĩa: đo được 135ms/lần nạp lại so với 12,6ms nếu cache theo tiến trình (nạp 1 lần, dùng lại cho mọi khung hình), tức chậm hơn gần 11 lần. Đây từng là lỗi thật trong `predict_vehicle.detect_vehicle_crop`, đã sửa bằng cách cache model vào một biến cấp module, cùng nguyên tắc với `_engine` cấp tiến trình đã dùng cho pipeline ONNX trong `app/services/ml_inference.py`.

### Số luồng CPU: điểm dễ sai thứ bảy, ảnh hưởng lớn hơn cả cache model

Pipeline nạp đồng thời 4-5 model nhỏ (YOLO định vị qua torch, detector biển của Đức, OCR, loại xe, kiểu dáng) và chạy TUẦN TỰ trên 1 ảnh, không theo lô. Mỗi `onnxruntime.InferenceSession` và torch mặc định tự phân luồng theo TOÀN BỘ số lõi logic của máy; 4-5 model cùng làm vậy trên 1 ảnh nhỏ khiến chi phí đồng bộ hoá luồng vượt xa thời gian tính toán thật. Đo trên máy dev 24 lõi logic: mặc định, pipeline tốn CPU-time khoảng 21 GIÂY cho 1 ảnh trong chưa tới 1 giây đồng hồ tường (tức đang tỏa ra hàng chục luồng chỉ để làm vài phép nhân ma trận nhỏ).

Ép mỗi model dùng cùng 1 số luồng cố định qua biến môi trường `ML_INTRAOP_THREADS` (đặt `intra_op_num_threads`/`inter_op_num_threads` cho từng session ONNX và `torch.set_num_threads()` cho nhánh torch) giải quyết vấn đề này. Mặc định là **1 luồng/model**, lựa chọn an toàn cho mọi máy kể cả Raspberry Pi 4/5 lõi, mục tiêu triển khai Edge của đồ án, nơi việc chia nhiều luồng còn dễ phản tác dụng hơn nữa.

### Hiệu năng: cách đo

Toàn bộ số hiệu năng dưới đây sinh ra từ một script duy nhất đã commit vào repo, chạy lại được bất cứ lúc nào:

```sh
python src/ml/benchmark_pipeline.py                       # cấu hình mặc định
ML_INTRAOP_THREADS=4 python src/ml/benchmark_pipeline.py  # cấu hình nhiều luồng
```

**Cấu hình máy đo.** Intel Core i7-13700K (16 lõi vật lý, 24 luồng logic, xung cơ bản 3,4GHz), 64GB RAM, Windows 11 Pro build 26200. Toàn bộ suy luận chạy trên **CPU**, không dùng GPU: đây là chủ ý, vì mục tiêu triển khai là thiết bị biên không có GPU rời, đo trên GPU sẽ cho con số không dùng được để suy ra hiệu năng thật lúc triển khai. Phần mềm: Python 3.14, onnxruntime 1.28.0 (`CPUExecutionProvider`), PyTorch 2.11.0, OpenCV 5.0.0, ultralytics 8.4.37.

**Đồng hồ đo.** Dùng `time.perf_counter()`, là đồng hồ đơn điệu độ phân giải cao của Python, đo **thời gian đồng hồ tường**, tức đúng khoảng thời gian người dùng phải chờ. Riêng phần chẩn đoán tranh chấp luồng dùng thêm `time.process_time()` (tổng thời gian CPU của mọi luồng trong tiến trình); tỉ số giữa hai đồng hồ này cho biết chương trình đang trải công việc ra trung bình bao nhiêu luồng, và chính chỉ số đó đã lộ ra lỗi toả luồng quá mức nói ở mục trên.

**Làm nóng trước khi đo (warm-up).** Bỏ 3 lượt chạy đầu, không tính vào kết quả. Lượt đầu tiên luôn chậm bất thường vì phải nạp trọng số từ đĩa, cấp phát bộ nhớ và chọn kernel CPU phù hợp: đo được lượt đầu của riêng bước định vị xe mất khoảng 615ms so với khoảng 10ms các lượt sau. Không bỏ warm-up thì trung bình bị số đầu tiên kéo lệch hoàn toàn.

**Thống kê báo cáo.** Chạy 10 lượt và báo cáo **trung vị**, không phải trung bình. Lý do: máy phát triển luôn có tiến trình nền (trình duyệt, IDE, đồng bộ đám mây) thỉnh thoảng chen vào làm một vài lượt tăng vọt; trung vị không bị các điểm ngoại lai đó kéo lệch. Bảng dưới in kèm min và max để thấy rõ mức dao động thật thay vì che đi.

**Phạm vi tính vào con số.** Chỉ tính phần tính toán của pipeline. **Không** tính thời gian đọc ảnh từ đĩa (`cv2.imread` chạy trước vòng đo), **không** tính thời gian truyền HTTP, mã hoá và lưu ảnh, ghi cơ sở dữ liệu ở backend. Đo riêng đầu-cuối qua API thật (`POST /captures/infer`, gồm cả các phần đó) cho khoảng 174ms mỗi lượt ở cấu hình 4 luồng, tức phần ngoài suy luận tốn thêm khoảng 100ms.

**Ảnh dùng để đo.** Ảnh mẫu đã commit sẵn trong repo `docs/research/assets/dataset-samples/1_bomaich_detect.png` (1200×600 px, pipeline phát hiện được 12 biển số trên ảnh này), để ai chạy lại cũng ở cùng điều kiện. Điều này quan trọng khi đọc số liệu: thời gian phụ thuộc nội dung ảnh, đặc biệt là **số biển phát hiện được**, vì bước màu biển và OCR chạy lặp cho từng biển. Ảnh camera cổng thật thường chỉ có 1 biển nên nhanh hơn ảnh mẫu này.

### Hiệu năng đo được

**Từng model ONNX chạy riêng lẻ** (đầu vào tensor ngẫu nhiên đúng kích thước, chỉ đo chi phí tính toán của đồ thị):

| Model | Kích thước ONNX | 1 luồng | 4 luồng |
|---|---:|---:|---:|
| Phát hiện biển (YOLOv8n) | 12,2 MB | 65,58 ms | 19,53 ms |
| OCR biển số (CRNN) | 1,7 MB | 1,14 ms | 0,48 ms |
| Loại xe (ResNet18) | 44,7 MB | 24,57 ms | 6,84 ms |
| Loại xe (MobileNetV3-Small) | 6,1 MB | 1,54 ms | 0,90 ms |
| Kiểu dáng xe (ResNet18) | 44,7 MB | 25,21 ms | 6,94 ms |

*(Lưu ý khi đọc bảng này: không được cộng các dòng lại thành thời gian pipeline. Chạy một mình thì mỗi model được dùng trọn số luồng cấu hình; trong pipeline chúng chạy nối tiếp và còn thêm chi phí tiền xử lý.)*

**Từng bước trong pipeline thật**, cùng ảnh, cùng tiến trình:

| Bước | 1 luồng (mặc định) | 4 luồng |
|---|---:|---:|
| Phát hiện biển số (ONNX) | 68,8 ms (40%) | 29,3 ms |
| Màu biển + OCR (12 biển) | 35,2 ms (21%) | 22,7 ms |
| Phân loại kiểu dáng (ONNX) | 26,5 ms (16%) | 10,1 ms |
| Phân loại loại xe (ONNX) | 24,8 ms (15%) | 8,9 ms |
| Định vị + cắt vùng xe (YOLO) | 11,2 ms (7%) | 11,9 ms |
| Tiền xử lý ảnh cho classifier | 2,6 ms | 3,1 ms |
| Chuyển màu BGR sang RGB | 1,2 ms | 1,4 ms |

**Toàn pipeline** (đúng cách backend và edge worker gọi):

| | 1 luồng (mặc định) | 4 luồng |
|---|---:|---:|
| Lượt đầu tiên (gồm nạp model) | 223,8 ms | 182,7 ms |
| Sau khi làm nóng, trung vị | **146,8 ms** | **76,2 ms** |
| Dao động (min đến max) | 145,7 đến 153,5 ms | 70,0 đến 86,3 ms |
| Số luồng dùng trung bình | 1,0 | 13,2 |

So với bản chưa cache model và chưa giới hạn số luồng (780 đến 900 ms mỗi ảnh, dao động rất mạnh 340 đến 1200 ms do tranh chấp luồng), cấu hình mặc định hiện tại nhanh hơn khoảng 6 lần và ổn định hơn hẳn: khoảng dao động thu từ hơn 800 ms xuống dưới 10 ms. Trên máy nhiều lõi, đặt `ML_INTRAOP_THREADS=4` còn nhanh gấp đôi nữa. Con số tối ưu phụ thuộc số lõi của máy chạy thật nên không đặt cứng trong code, chỉ đổi qua biến môi trường lúc triển khai; mặc định để 1 vì đó là giá trị an toàn trên mọi máy kể cả Raspberry Pi 4 lõi.

Bước phát hiện biển số (module của Đức) là bước tốn thời gian nhất ở cả 2 cấu hình (40% và 34% tổng thời gian), không phải bước loại xe hay kiểu dáng của chương này; nếu cần tối ưu tiếp thì nên ưu tiên bước đó trước. Số đo thật trên Raspberry Pi 5 vẫn để dành cho bước sau.

**Bước định vị xe (YOLO coarse) có 2 backend chọn được, không chỉ dùng cứng torch.** Ban đầu đo thử xuất `yolov8n.pt` sang ONNX bằng cách resize thẳng về hình vuông 640×640 (squash-resize, giống cách module biển số của Đức đang làm): kết quả chậm hơn hẳn bản torch (70ms so với 13,4ms) VÀ có lỗi nghiêm trọng hơn, trên ảnh camera cổng thật (khung hình rộng, vd 2048×899) squash-resize làm méo xe đến mức model không phát hiện được xe nào. Nguyên nhân: `ultralytics` tự letterbox (co ảnh giữ tỉ lệ khung hình rồi đệm xám, không squash), còn resize thẳng phá vỡ tỉ lệ đó.

Sau khi viết đúng letterbox cho nhánh ONNX (`predict_vehicle.CoarseVehicleDetector`, tái dùng `decode_v8` của module biển số cho phần giải mã box/NMS), kết quả ONNX gần như giống hệt bản torch trên cùng ảnh (car, độ tin cậy 0,853 so với 0,850, box lệch vài pixel), xác nhận letterbox đúng là điều kiện bắt buộc, không phải tùy chọn. Tốc độ vẫn chậm hơn torch trên máy dev x86 hiện tại: đo cùng điều kiện với bảng hiệu năng ở trên (cùng ảnh mẫu, cùng 1 luồng, cùng cách đo), tổng pipeline là **218,5 ms** với backend ONNX so với **147,3 ms** với backend `.pt`, do bản ONNX xuất tĩnh luôn phải xử lý đủ khung 640×640 trong khi `ultralytics` tự co ảnh theo tỉ lệ nên vùng xử lý thật nhỏ hơn. Đổi lại **không cần cài `torch`/`ultralytics`** cho bước này, quan trọng khi triển khai trên thiết bị muốn tránh phụ thuộc torch. Lý do: gói `ultralytics` khai báo cứng `torch`/`torchvision` là dependency bắt buộc trong chính pip metadata của nó, nên chỉ cần còn `from ultralytics import YOLO` trong code là bắt buộc phải cài torch trên thiết bị, bất kể model là `.pt` hay `.onnx`.

Vì vậy, thay vì chốt cứng một lựa chọn, `CoarseVehicleDetector` hỗ trợ cả 2 backend, chọn qua đường dẫn trọng số (đuôi `.onnx` dùng onnxruntime thuần, còn lại dùng `.pt` qua ultralytics), cùng quy ước với `PlateDetector` của module biển số. Mặc định vẫn là `.pt` (nhanh hơn trên CPU x86 thường gặp ở máy dev/server); đổi sang `.onnx` qua biến môi trường `ML_COARSE_WEIGHTS` khi triển khai một thiết bị không muốn cài torch. Đây đúng theo cách ngành công nghiệp thường làm: dùng framework train (ultralytics/torch) trên máy phát triển, xuất sang định dạng trung gian (ONNX), rồi chạy trên thiết bị bằng runtime suy luận tối giản với tiền/hậu xử lý tự viết tay, không mang cả framework train theo thiết bị. Riêng phần tiền xử lý ảnh của 2 model tự huấn luyện (loại xe, kiểu dáng, dùng `torchvision.transforms`) và giải mã CTC của OCR vẫn còn phụ thuộc torch cho các phép toán đơn giản (resize/chuẩn hóa, argmax); muốn bỏ hẳn torch khỏi toàn bộ pipeline cần viết lại thêm 2 chỗ này bằng numpy/cv2 thuần, để dành cho khi thật sự cần triển khai một thiết bị không cài được torch.

### Chọn model nào

Cả 2 bước (loại xe và kiểu dáng) đều có 2 phương án kiến trúc. Ở bước kiểu dáng, hai kiến trúc gần như ngang nhau về độ chính xác (0,8997 so với 0,9007), nhưng MobileNetV3-Small nhẹ hơn 7,3 lần và nhanh hơn gần 2 lần trên CPU. Ở bước loại xe, ResNet18 chính xác hơn rõ hơn một chút (0,9866 so với 0,9799 trên tập test, và đặc biệt là 100% so với 92% trên bộ kiểm tra OOD ở mục 5.4), nên pipeline hiện đang dùng ResNet18 làm mặc định cho bước này dù nặng hơn. Với mục tiêu chạy trên Raspberry Pi 5, MobileNetV3-Small vẫn là lựa chọn đáng cân nhắc lại cho cả 2 bước nếu độ trễ trên Pi thật sự là điểm nghẽn. Quyết định cuối cùng vẫn chờ số đo thật trên Pi 5.

## 5.7 Kết luận

Công việc đã hoàn thành:

- Khảo sát và chốt nguồn dữ liệu cho bài toán phân loại kiểu dáng xe, gộp 12 kiểu dáng gốc của B5 thành 3 nhóm phù hợp nhu cầu vận hành bãi xe, xử lý được 10.000 ảnh crop chia sẵn train/valid/test.
- Huấn luyện và so sánh 2 kiến trúc ResNet18 và MobileNetV3-Small cho bước kiểu dáng, đạt accuracy 0,8997 và 0,9007 trên tập test, kèm đầy đủ ma trận nhầm lẫn, đường hội tụ và số liệu tài nguyên thật.
- Huấn luyện riêng model cho bước loại xe (`car`/`motorbike`/`truck`) thay cho việc dùng thẳng nhãn COCO của YOLO pretrained, đạt accuracy 0,9866 (ResNet18) và 0,9799 (MobileNetV3-Small) trên tập test, thu hẹp khoảng cách với yêu cầu đề cương từ 4/4 xuống còn 1/4 lớp (`bus`) chưa có model riêng.
- Phát hiện và sửa một lỗi học tắt (shortcut learning) ở lần huấn luyện đầu của model loại xe (100% test nhưng 1/13 đúng trên ảnh OOD), bằng cách trộn nguồn ảnh cho mỗi lớp; dựng một bài test OOD cố định (`sanity_check_vehicle_type_ood.py`) làm bài kiểm tra hồi quy lâu dài, không chỉ chạy một lần.
- Tích hợp cả 2 bước vào pipeline thật dùng chung cho backend và edge worker (`onnx_pipeline.py`), phát hiện và sửa 2 lỗi hiệu năng/tích hợp: model định vị bị nạp lại từ đĩa mỗi khung hình (135ms → 12,6ms sau khi cache), và tranh chấp luồng CPU giữa nhiều model chạy đồng thời (780-900ms/ảnh, dao động mạnh → ổn định 146,8ms/ảnh, xuống 76,2ms trên máy nhiều lõi qua biến môi trường `ML_INTRAOP_THREADS`). Mọi số hiệu năng đều sinh từ script `benchmark_pipeline.py` đã commit, chạy lại được để đối chiếu. Sửa cùng lúc phát hiện và khắc phục luôn lỗi tên nhãn `motorcycle`/`motorbike` khiến xe máy không được gán nhóm phí tự động.
- **Đo lại chất lượng ở mức pipeline chứ không chỉ mức model, và sửa lỗi nặng nhất phát hiện được từ đó** (mục 5.4): bước định vị YOLO pretrained từng được đặt làm điều kiện chạy của model loại xe, khiến 57% số ảnh trong tập test không hề được phân loại dù model xử lý được. Sau khi tách hai bước độc lập và cho model loại xe chạy trên cả khung hình đúng như lúc huấn luyện, tỉ lệ ảnh có kết quả tăng từ 43% lên 100% và độ chính xác end-to-end từ 41,6% lên 98,7%, khớp đúng accuracy 98,66% của bản thân model.
- Xuất model sang ONNX cho cả 2 kiến trúc của cả 2 bước, sẵn sàng cho bước triển khai trên thiết bị biên.
- Viết notebook tổng hợp kết quả huấn luyện và hướng dẫn tích hợp cho bước tiếp theo.

Ba điểm cần lưu ý khi đánh giá kết quả. Thứ nhất, lớp `bus` vẫn chưa có model riêng và nay cũng không còn dùng nhãn COCO làm phương án tạm (đo được nhãn đó sai 2/2 lần, mục 5.4), nên xe khách sẽ bị xếp vào một trong 3 lớp hiện có cho tới khi nhân viên sửa tay; cần bổ sung dữ liệu xe khách đúng góc camera cổng để huấn luyện nốt. Thứ hai, model kiểu dáng vẫn huấn luyện hoàn toàn trên dữ liệu ảnh dealer/showroom (B5) nên con số 90% chưa phản ánh được hiệu năng trên ảnh camera giám sát Việt Nam thật, dù model loại xe đã được kiểm chứng tốt hơn qua bộ OOD thật. Thứ ba, các số đo hiệu năng CPU trong chương này đều đo trên máy phát triển (24 lõi logic), chưa phải Raspberry Pi 5 mục tiêu triển khai; hành vi số luồng tối ưu trên Pi nhiều khả năng khác hẳn máy dev (ít lõi hơn, mặc định 1 luồng/model nhiều khả năng vẫn là lựa chọn đúng). Cả ba điểm này để lại cho các tuần tiếp theo, hướng cụ thể đã nêu ở mục 5.5.

---

**Tài liệu tham khảo:**
- He, K. et al. (2016). "Deep Residual Learning for Image Recognition." CVPR. (ResNet)
- Howard, A. et al. (2019). "Searching for MobileNetV3." ICCV.
- Jocher, G. et al. Ultralytics YOLOv8 (2023). Dùng bản pretrained COCO cho bước định vị xe, không huấn luyện thêm.
