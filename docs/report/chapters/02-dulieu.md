# Chương 2: Thu thập và xử lý dữ liệu

Chương này trình bày quá trình tìm hiểu, đánh giá và bước đầu lựa chọn dữ liệu công khai cho các module của hệ thống - phát hiện biển số, OCR, phân loại màu biển và phân loại xe. 
- Nhật: thực hiện mục 2.1–2.2, tập trung vào dataset phát hiện biển số Việt Nam; 
- Đức: thực hiện mục 2.3, mở rộng sang dataset OCR, ký tự, màu biển và phân loại xe.

## 2.1 Khảo sát bộ dữ liệu công khai

Nhóm đã research các dataset công khai và đã xem qua 14 dataset, chia làm 3 nhóm: (A) biển số Việt Nam, (B) phương tiện/bối cảnh đường phố Việt Nam, (C) các dataset ALPR/bãi xe nước ngoài để đối chiếu. Mỗi dataset được kiểm tra trực tiếp trên trang nguồn (license, mô tả, ngày kiểm tra) trước khi đưa vào bảng so sánh dưới đây.

### 2.1.1 Nhóm A - Biển số Việt Nam

| Ký hiệu | Tên / nguồn | Host | Số ảnh | Classes | License | Biển 1 hàng/2 hàng? |
|---|---|---|---|---|---|---|
| A1 | [Vietnam License Plate Segment (duydieunguyen)](https://www.kaggle.com/datasets/duydieunguyen/licenseplates) | Kaggle | ~5.000 | 2 (1 hàng: 3.510 / 2 hàng: 1.625) | Unknown - cần hỏi lại tác giả | Có, tách rõ số lượng |
| A2 | [Vietnamese Car License Plate (Cuong Ta)](https://universe.roboflow.com/cuong-ta-ulxex/vietnamese-car-license-plate) | Roboflow | 8.255 | 1 (plate, không OCR) | CC0 1.0 | Không rõ tỷ lệ |
| A3 | [vietnamese-license-plate-tptd0 (school-fuhih)](https://universe.roboflow.com/school-fuhih/vietnamese-license-plate-tptd0) | Roboflow | 8.397 | 1 (plate, không OCR) | CC BY 4.0 | Không rõ tỷ lệ |
| A4 | [Motorcycle License Plate (HaUI)](https://universe.roboflow.com/hanoi-university-of-industry/motorcycle-license-plate) | Roboflow | 1.748 | 1 (plate, không OCR) | MIT | Thiên về xe máy (2 hàng), chưa rõ tỷ lệ chính xác |
| A5 | [greenParking (thaiphung)](https://universe.roboflow.com/thaiphung/greenparking) | Roboflow | 1.748 | 1 (không đặt tên) | CC BY 4.0 | Không xác định - trang không có mô tả |
| A6 | [Viet Nam OCR plate (license-plate-reg)](https://universe.roboflow.com/license-plate-reg/viet-nam-ocr-plate) | Roboflow | 3.819 | 32 (theo ký tự, có OCR ground truth) | CC0 1.0 | Không rõ tỷ lệ |
| A7 | [VNLicensePlate_yolov7 (bomaich)](https://www.kaggle.com/datasets/bomaich/vnlicenseplate) | Kaggle | 1.000 | plate (1&2 hàng nhưng gộp chung) | Unknown | Có, nhưng không tách số |

Không dataset nào ở nhóm A ghi rõ điều kiện ánh sáng hay bối cảnh chụp trong mô tả. A1 kà dataset được ưu tiên vì có 2 loại biển số ngang và dọc, là 2 loại biển phổ biển ở việt nam theo quy định.

Sau khi xem trực tiếp ảnh mẫu, A2 (Cuong Ta) cũng có độ đa dạng biển số khá tốt cho nhiều loại xe, không chỉ ô tô như tên gợi ý. Cùng với A1, đây là 2 dataset nhóm ưu tiên xem xét thêm cho riêng bài toán detect vùng biển số.

### 2.1.2 Nhóm B - Phương tiện, bối cảnh đường phố/bãi xe Việt Nam

| Ký hiệu | Tên / nguồn | Host | Số ảnh | Classes | License | Ghi chú |
|---|---|---|---|---|---|---|
| B1 | [Vietnamese vehicle (car-classification, v3)](https://universe.roboflow.com/car-classification/vietnamese-vehicle/dataset/3) | Roboflow | 1.547 | 8 lớp "remapped", chưa xem được danh sách cụ thể | CC BY 4.0 | Mô tả gốc là 4 lớp car/bus/truck/motorcycle trước khi remap |
| B2 | [Vehicle Vietnam-CanTho](https://universe.roboflow.com/vehicle/vehicle-vietnam-cantho-2gxc8) | Roboflow | 1.110–1.746 | 4 (Car/Truck/Bus/Motorbike) | CC BY 4.0 | Chỉ có ảnh ban ngày, đường phố Cần Thơ |
| B3 | [UIT-CVID21 (UIT-Together)](https://uit-together.github.io/datasets/) | GitHub (UIT) | 10.000 (chưa xem được thật) | 4 (Bus/Car/Truck/Van) | Không rõ - link trả lỗi 404 khi mở (2026-07-30) | Chụp từ drone, khác góc camera cổng bãi xe |
| B4 | [QuangTranUTE/Vehicle-Detection](https://github.com/QuangTranUTE/Vehicle-Detection) | GitHub | ~11.000 | Không rõ | Không rõ | Camera giám sát giao thông, không phải bãi xe |
| B5 | [Vehicle Body Style Dataset (Roboflow, gốc dựa theo CompCars)](https://universe.roboflow.com/research-projects-qodgb/vehicle-body-style-dataset) | Roboflow | 10.000 (7.014 train / 1.999 valid / 987 test) | 12 kiểu dáng (Sedan, SUV, Hatchback, MPV, Pickup, Coupe, Wagon, Convertible, Sports, Hardtop Convertible...) | CC BY 4.0 | Ảnh chụp kiểu dealer/showroom, bối cảnh gốc Trung Quốc |

Ở nhóm B, B1–B4 chưa có dataset Việt Nam nào tách phương tiện theo kiểu dáng (sedan/SUV/pickup) - tất cả chỉ dừng ở mức "Car" chung. Nhóm tìm thêm B5 để bù khoảng trống này. Nhóm đã downloađ và chạy EDA trên B5 cho thấy: 12 lớp cân bằng gần như tuyệt đối (chênh lệch max/min chỉ 1,02 lần), nhưng ảnh chủ yếu chụp kiểu dealer/showroom (đo qua tỉ lệ diện tích xe/ảnh trung bình 0,31 - cao hơn hẳn ảnh camera giám sát cổng bãi xe ở nhóm A/C, chỉ khoảng 0,03–0,04) và bối cảnh gốc Trung Quốc (biển hiệu chữ Hán, theo nguồn CompCars). Đây không phải khác biệt về hình dáng xe - sedan/SUV/pickup về thiết kế khá phổ quát giữa các thị trường - mà là khác kiểu ảnh chụp (studio/quảng cáo so với camera giám sát) và khác phân bố model xe theo thị trường Trung Quốc so với Việt Nam. N
hóm chọn dùng B5 trước để đánh giá tính khả quan của hướng pretrain trên B5 rồi fine-tune bằng ảnh thực tế Việt Nam (Nhật, Tuần 5); nếu không đáp ứng (ví dụ thiếu hẳn lớp motorbike, hoặc car-subtype lệch nhiều do phân bố model) sẽ bổ sung thêm dataset khác thay vì thay hẳn nguồn chính.

### 2.1.3 Nhóm C - ALPR/bãi xe nước ngoài (đối chiếu)

| Ký hiệu | Tên / nguồn | Số ảnh | License | Bối cảnh | Ánh sáng |
|---|---|---|---|---|---|
| C1 | [CCPD (Trung Quốc)](https://github.com/detectRecog/CCPD) | \>300.000 | MIT | Bãi xe TQ | 61,4% ngày / 38,6% đêm - dataset duy nhất định lượng rõ tỷ lệ này |
| C2 | [PKLot (Brazil)](https://public.roboflow.com/object-detection/pklot) | 12.416 (+695k patch) | CC BY 4.0 | Bãi xe ngoài trời | Nhiều kiểu thời tiết nhưng không có ảnh đêm |
| C3 | [CNRPark(+EXT) (Ý)](http://cnrpark.it/) | 12.000 (+~145–150k patch) | Chưa kiểm tra được (lỗi certificate khi truy cập) | Bãi xe ngoài trời | Nhiều thời tiết, có cả ảnh đêm/thiếu sáng |
| C4 | [AOLP (Đài Loan)](https://sites.google.com/site/avlabaolp/download) | 2.049 | Chỉ dùng học thuật, cấm thương mại, phải xin phép bằng văn bản | Cổng ra vào/phạt nguội/tuần tra | 3 kịch bản góc chụp khác nhau |
| C5 | [OpenALPR benchmarks (US/EU/BR)](https://github.com/openalpr/benchmarks) | EU 108 / US ~222 | AGPL-3.0 | Chỉ dùng đối chiếu, quy mô nhỏ | Không kiểm tra |

Nhóm C dùng biển số nước ngoài nên không dùng để train OCR biển VN được, nhưng CCPD (C1) có thể tham khảo để pretrain phần detect vùng biển số nói chung, vì đây là dataset duy nhất trong cả 3 nhóm có số liệu ngày/đêm rõ ràng - điều mà cả nhóm A lẫn B đều thiếu.

### 2.1.4 Đánh giá và hướng chọn ban đầu

Nhóm chọn A1 làm dataset huấn luyện chính, vì là bộ duy nhất tách rõ biển 1 hàng/2 hàng (BSD/BSV); A3, A4 dùng bổ sung. Cả 3 được tải về và làm EDA ở mục 2.2.

## 2.2 Phân tích khám phá dữ liệu (EDA)

Mô tả trên trang Roboflow/Kaggle không nói gì về ánh sáng hay bối cảnh chụp, nên nhóm tải cả 3 dataset về và tự làm EDA (đếm ảnh, đo kích thước, độ sáng, xem ảnh mẫu) để biết thực tế thế nào. Kết quả tổng hợp:

| Dataset | Số ảnh | Số object | Độ phân giải (px) | Độ sáng TB | % ảnh tối |
|---|---|---|---|---|---|
| A3 | 8.357 | 8.548 | 640×640 (cố định) | 100,7 | 12,8% |
| A4 | 1.748 | 1.748 | 472×303 (cố định) | 111,1 | 0,0% |
| A1 | 4.578 | 5.200 | 380–4032 × 285–3024 | 102,1 | 10,7% |

*(Độ sáng đo trên mẫu ngẫu nhiên n=600 ảnh/bộ, seed cố định = 42, để không phải đọc hết 14.683 ảnh)*

### 2.2.1 Phân bố class và kích thước biển số

![Phân bố số lượng object gán nhãn theo dataset và theo lớp](../figures/eda_class_distribution.png)

Ở A1, lớp `BSV` (biển 2 hàng, 3.559 đối tượng) nhiều gấp khoảng 2,2 lần lớp `BSD` (biển 1 hàng, 1.641 đối tượng). Nếu gộp cả 3 dataset lại để train thì cần để ý điểm lệch này, không thì model sẽ học thiên về biển 2 hàng.

![Phân bố tỉ lệ diện tích biển số / diện tích ảnh](../figures/eda_plate_area_ratio.png)

Biểu đồ trên là tỉ lệ diện tích vùng biển số so với cả ảnh (`box_area_ratio`), dùng để đoán ảnh là cận cảnh biển số hay chụp xa. Trung bình chỉ khoảng 0,028–0,043 ở cả 3 bộ, tức là phần lớn ảnh chụp toàn cảnh đầu xe chứ không phải cận cảnh sát biển số.

### 2.2.2 Kích thước ảnh và độ sáng

![Kích thước ảnh, tỉ lệ khung hình và phân bố độ sáng](../figures/eda_size_brightness.png)

Khi đo kích thước ảnh mới phát hiện ra là A3 và A4 đã bị Roboflow resize về đúng một kích thước cố định lúc export (640×640 cho A3, 472×303 cho A4 - độ lệch chuẩn kích thước bằng 0), nên độ phân giải gốc coi như mất hết. Chỉ A1 (tải trực tiếp từ Kaggle, không qua Roboflow) là còn giữ được kích thước gốc, dao động 380 đến 4032 pixel chiều rộng.

Vì không dataset nào có nhãn ánh sáng thật, nhóm dùng độ sáng trung bình ảnh xám (thang 0–255) làm proxy tạm: dưới 70 coi là tối/thiếu sáng, trên 190 là quá sáng. A4 gần như không có biến thiên gì (gần 100% rơi vào mức "bình thường"), còn A3 và A1 có khoảng 11–13% ảnh rơi vào mức tối. Đây chỉ là proxy dựa theo độ sáng pixel thôi, không phải nhãn thật về điều kiện chụp (trong nhà/ngoài trời, ngày/đêm).

### 2.2.3 Xem ảnh mẫu để kiểm tra bối cảnh

![Ảnh mẫu ngẫu nhiên từ ba bộ dữ liệu, minh họa bối cảnh camera cổng bãi xe](../figures/eda_sample_context.png)

Ban đầu, do trang Roboflow/Kaggle không mô tả gì về điều kiện chụp, nhóm nghĩ có thể phải tự chụp thêm gần như toàn bộ ảnh ở bối cảnh cổng bãi xe. Nhưng khi mở thử vài chục ảnh mẫu ra xem thì hóa ra cả 3 dataset đều là ảnh chụp thật từ camera cổng bãi xe/hầm gửi xe, có thanh chắn (boom barrier) trong khung hình - đúng bối cảnh đồ án cần, không phải ảnh đường phố chụp ngẫu nhiên như suy đoán ban đầu. Nhiều ảnh còn có timestamp cháy vào góc kiểu camera an ninh DVR, và có vài ảnh chụp trong hầm xe thiếu sáng. Đây là bài học rút ra: mô tả text trên trang dataset không đủ để đánh giá, phải tải và xem ảnh thật mới biết chắc được.

## 2.3 Dataset bổ sung cho OCR, ký tự, màu biển và phân loại xe

Song song với phần khảo sát biển số ở mục 2.1–2.2, Đức khảo sát và tải thật các dataset phục vụ OCR, nhận dạng ký tự, phân loại màu biển, và phân loại loại xe. Toàn bộ số liệu dưới đây lấy từ tải thật và đọc file thật (đếm ảnh/box, đọc `data.yaml`, phân tích màu HSV trên crop thật), không suy đoán từ mô tả trang nguồn.

### 2.3.1 Dataset detect biển, OCR và ký tự

| Dataset | Nguồn | Số ảnh (thật) | Format | Ghi chú |
|---|---|---|---|---|
| plate_tanhphp | [Kaggle tanhphp](https://www.kaggle.com/datasets/tanhphp/vietnamese-license-plates) | 2.255 (2.998 box) | YOLO bbox, nc=1 | Dùng làm nguồn detect chính bổ sung |
| plate_bomaich_yolov7 | [Kaggle bomaich](https://www.kaggle.com/datasets/bomaich/vnlicenseplate) | 498 (780 box) | YOLO bbox, split sẵn | Ảnh cảnh đầy đủ, dùng bổ sung |
| plate_ocr_topkek | [Kaggle topkek69](https://www.kaggle.com/datasets/topkek69/vietnamese-license-plate-ocr) | 12.190 (6.643 crop thật + 5.547 sinh) | Crop + CSV `Name,Label,Type` (vd `30F 11292`) | Nguồn OCR chính; cần tách riêng phần sinh tổng hợp khi đánh giá để không thổi phồng accuracy |
| motorbike_ocr_100 | [Kaggle dtkngan](https://www.kaggle.com/datasets/dtkngan/100-bien-so-xe-may-ocr) | 116 | Ảnh + chuỗi biển (vd `59N187515`) | Test set riêng cho biển xe máy 2 hàng, chỉ có ảnh ban ngày |
| char_nguyenquanglinh | [Kaggle nguyenquanglinh0109](https://www.kaggle.com/datasets/nguyenquanglinh0109/character-dataset-for-vietnam-license-plate) | 1.839 | Folder = class, ảnh 28×28 | Lệch lớp nặng giữa các ký tự (đo được M=4, F=148) - cần augment mạnh cho ký tự hiếm |

Cùng với `plate_segment_duydieu` (A1 ở mục 2.1, 4.578 ảnh) dùng cho việc tách luồng biển 1 hàng/2 hàng, đây là bộ dataset detect + OCR + ký tự đầy đủ nhất mà nhóm có được. Không kho lưu trữ nào trong nhóm này đi kèm file LICENSE rõ ràng, trừ `vehicle_lmphmthanh` (CC BY 4.0 nhúng sẵn trong `data.yaml`) - các bộ còn lại chỉ có ghi chú license trên trang Kaggle, nên nhóm chỉ dùng để huấn luyện nội bộ, không phát hành lại.

### 2.3.2 Phân tích màu biển số (HSV)

Để phục vụ module phân loại màu biển (Đức, Tuần 3), nhóm chạy phân tích màu HSV trên 599 crop biển số thật (từ `plate_ocr_topkek`), tách nền sáng ra khỏi vùng chữ tối:

| Màu | Số crop | Tỉ lệ | Ý nghĩa biển VN |
|---|---|---|---|
| Trắng | 372 | 62,1% | Xe cá nhân |
| Vàng | 115 | 19,2% | Xe kinh doanh/dịch vụ |
| Xanh dương | 57 | 9,5% | Cơ quan nhà nước |
| Đỏ | 37 | 6,2% | Quân đội |

Bốn màu chính (trắng/vàng/xanh dương/đỏ) tách được rõ ràng thành các cụm hue/saturation riêng biệt trên không gian HSV, nên hướng dùng HSV + CLAHE (không cần CNN riêng cho màu) là khả thi. Dữ liệu lệch nặng về màu trắng (62%) - nếu sau này đổi sang huấn luyện CNN cho màu thì cần xử lý mất cân bằng lớp, còn với HSV chỉ cần tinh chỉnh ngưỡng. Đồ án tập trung phân loại chính giữa trắng và vàng (xe cá nhân/kinh doanh), là 2 màu chiếm đa số trong dữ liệu.

### 2.3.3 Dataset cho phân loại xe

Cho module phân loại xe (Nhật, Tuần 5), nhóm chốt dùng **A1 - Vietnam License Plate Segment (duydieunguyen, mục 2.1.1)** và **B1 - Vietnamese vehicle car-classification v3 (mục 2.1.2)**. A1 dùng làm proxy cho phân loại 2 lớp ô tô/xe máy qua nhãn biển dài (`BSD`, đặc trưng biển ô tô 1 hàng) và biển vuông (`BSV`, đặc trưng biển xe máy 2 hàng); B1 dùng để pretrain hình dạng xe. Việc phân loại đầy đủ hơn (tách riêng xe tải, xe buýt) sẽ bổ sung sau nếu cần.

## 2.4 Kết Luận

- **Detect biển:** A1 (dataset biển số VN, mục 2.1) làm nền chính, A3/A4 bổ sung, cùng `plate_tanhphp` và `plate_bomaich_yolov7` (mục 2.3.1).
- **OCR:** `plate_ocr_topkek` làm nguồn chính, `motorbike_ocr_100` làm test set riêng cho biển 2 hàng.
- **Màu biển:** không cần dataset gán nhãn riêng - dùng trực tiếp HSV + CLAHE trên crop biển đã có (mục 2.3.2).
- **Phân loại xe:** B5 — Vehicle Body Style Dataset (mục 2.1.2) làm nguồn chính để pretrain + fine-tune phân loại kiểu dáng (sedan/SUV/pickup...) ở Tuần 5, đánh giá tính khả quan trước khi quyết định bổ sung dataset khác nếu cần; A1 dùng làm proxy BSD/BSV cho 2 lớp ô tô/xe máy trong giai đoạn đầu (mục 2.3.3).

---

**Tài liệu tham khảo:**
- Xu, Z. et al. (2018). "Towards End-to-End License Plate Detection and Recognition: A Large Dataset and Baseline." ECCV. (CCPD)
- Almeida, P. R. L. et al. (2015). "PKLot - A Robust Dataset for Parking Lot Classification." Expert Systems with Applications.
- Amato, G. et al. (2017). "Deep Learning for Decentralized Parking Lot Occupancy Detection." Expert Systems with Applications. (CNRPark+EXT)
