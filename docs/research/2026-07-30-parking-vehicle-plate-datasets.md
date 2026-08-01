# Khảo sát bộ dữ liệu công khai: biển số Việt Nam + phương tiện/bãi xe

**Ngày tạo:** 2026-07-30 · **Mode:** 3 (dataset research)
**Mục đích:** Tuần 2 — Task 2 (tìm và tải dataset công khai, đánh giá mức độ đáp ứng về ánh sáng và bối cảnh, chỉ tự chụp bổ sung nếu chưa đủ).

---

## A. Bộ dữ liệu biển số Việt Nam (detection + OCR)

### A1. Kaggle — "Vietnam License Plate Segment Datasets" (duydieunguyen) — ưu tiên hàng đầu

| Mục | Nội dung |
|---|---|
| URL / host | [kaggle.com/datasets/duydieunguyen/licenseplates](https://www.kaggle.com/datasets/duydieunguyen/licenseplates) — Kaggle |
| Size | ~5.000 ảnh: 3.510 biển 1 hàng (LpD) + 1.625 biển 2 hàng (LpV), chia 70/30 train/eval; 9.157 file, 1,01 GB |
| Classes / format | 2 class (biển 1 hàng vs 2 hàng); nhãn dạng polygon 4 góc biển (định dạng YOLO, kèm `dataset.yaml`) |
| License | Ghi "Unknown" trên Kaggle — cần liên hệ tác giả xác nhận điều khoản trước khi sử dụng chính thức, dù Điều khoản dịch vụ của Kaggle nhìn chung cho phép sử dụng phi thương mại/nghiên cứu |
| Plate types | Dataset duy nhất trong khảo sát này công bố rõ số lượng tách riêng biển 1 hàng và 2 hàng — phù hợp trực tiếp với yêu cầu đề tài |
| Lighting/bối cảnh | Mô tả ghi "thu thập từ internet và môi trường thực tế với điều kiện, thời tiết, góc camera đa dạng" nhưng không có số liệu định lượng cụ thể về tỷ lệ ngày/đêm |
| Đánh giá | Cỡ mẫu vừa phải, tách rõ biển 1 hàng/2 hàng bằng số liệu cụ thể — bám sát yêu cầu đề tài nhất trong nhóm biển số Việt Nam, nhược điểm là license chưa xác định rõ. Nhóm ưu tiên dataset này hàng đầu (top 1) |

Nguồn: [r.jina.ai render 2026-07-30](https://r.jina.ai/https://www.kaggle.com/datasets/duydieunguyen/licenseplates).

---

### A2. Roboflow — "Vietnamese Car License Plate" (Cuong Ta) — top 2

| Mục | Nội dung |
|---|---|
| URL / host | [universe.roboflow.com/cuong-ta-ulxex/vietnamese-car-license-plate](https://universe.roboflow.com/cuong-ta-ulxex/vietnamese-car-license-plate) — Roboflow Universe |
| Size | 8.255 ảnh theo trang (8.254 ảnh thực tế tải về được — 5.777 train / 2.477 valid / 0 test), 8.445 object gán nhãn |
| Classes / format | 1 class `plate` — chỉ detect vùng biển (bbox), không có OCR ground truth |
| License | Public Domain — CC0 1.0 (xác nhận qua r.jina.ai, và qua `data.yaml` sau khi tải) |
| Plate types | Không nêu tỷ lệ biển 1 hàng/2 hàng trong mô tả trang; tên gọi "Car License Plate" gợi ý thiên về biển ô tô, nhưng theo xem trực tiếp ảnh mẫu (nhóm tự kiểm tra và xác nhận lại qua EDA), dataset thực tế có cả ô tô (Toyota, Nissan, Kia...) lẫn xe máy tại cùng bối cảnh camera cổng bãi xe, không chỉ thiên về ô tô |
| Lighting/bối cảnh | Trang không có mô tả định lượng; EDA thực tế (notebook `src/ml/notebooks/eda-plate-datasets.ipynb`) đo được: độ sáng trung bình 100,0 (thang 0–255), 13,7% ảnh rơi vào mức "tối/thiếu sáng" theo proxy độ sáng pixel — tương đương các dataset khác đã khảo sát, không có ảnh đêm rõ rệt |
| Độ phân giải (qua EDA) | 240–2000 × 160–1500 px, không bị resize cố định khi export (khác với A3/A4 — xem mục H) |
| Đánh giá | Cỡ lớn nhất trong nhóm biển Việt Nam đã khảo sát, license CC0 dễ sử dụng nhất (Public Domain, không cần ghi công), và qua xem mẫu thực tế + EDA có độ đa dạng biển số tốt cho nhiều loại xe, còn giữ được độ phân giải gốc — cùng với A1, đây là top 2 dataset nhóm ưu tiên cho bài toán detect vùng biển số |

Nguồn: [r.jina.ai render 2026-07-30](https://r.jina.ai/https://universe.roboflow.com/cuong-ta-ulxex/vietnamese-car-license-plate); số liệu EDA thực tế 2026-07-30 (notebook `src/ml/notebooks/eda-plate-datasets.ipynb`, số liệu tại `docs/research/eda_outputs/eda_summary.csv`).

---

### A3. Roboflow — "vietnamese-license-plate" (school-fuhih)

| Mục | Nội dung |
|---|---|
| URL / host | [universe.roboflow.com/school-fuhih/vietnamese-license-plate-tptd0](https://universe.roboflow.com/school-fuhih/vietnamese-license-plate-tptd0) — Roboflow Universe |
| Size | 8.397 ảnh, publish 8/2023 |
| Classes / format | 1 class (biển số Việt Nam nói chung) — detection, không OCR ground truth |
| License | CC BY 4.0 |
| Plate types | Không phân biệt 1 hàng/2 hàng trong metadata |
| Lighting/bối cảnh | Không có mô tả; trang có công bố kết quả model pretrain đạt mAP@50 99,5% — số liệu này do tác giả tự công bố, chưa qua phản biện độc lập và có khả năng chỉ phản ánh việc overfit trên tập test cùng phân phối |
| Đánh giá | Cỡ tương đương A2, license CC BY yêu cầu ghi công nguồn nếu sử dụng |

Nguồn: [r.jina.ai render 2026-07-30](https://r.jina.ai/https://universe.roboflow.com/school-fuhih/vietnamese-license-plate-tptd0).

---

### A4. Roboflow — "Motorcycle license plate" (Hanoi University of Industry)

| Mục | Nội dung |
|---|---|
| URL / host | [universe.roboflow.com/hanoi-university-of-industry/motorcycle-license-plate](https://universe.roboflow.com/hanoi-university-of-industry/motorcycle-license-plate) — Roboflow Universe |
| Size | 1.748 ảnh, publish 1/2023, 461 views / 28 downloads |
| Classes / format | 1 class `license-plate` — detection, không OCR ground truth |
| License | MIT |
| Plate types | Tên gọi nhắm riêng biển xe máy (nhiều khả năng là biển 2 hàng, nhưng trang không xác nhận tỷ lệ cụ thể) |
| Lighting/bối cảnh | Không có mô tả |
| Đánh giá | Dataset duy nhất trong khảo sát này do một cơ sở đào tạo khác tại Việt Nam (Đại học Công nghiệp Hà Nội) công bố riêng cho biển xe máy — bổ sung cho A2/A3 vốn không tách loại xe, tuy cỡ mẫu nhỏ hơn đáng kể (1.748 so với khoảng 8.000) |

Nguồn: [r.jina.ai render 2026-07-30](https://r.jina.ai/https://universe.roboflow.com/hanoi-university-of-industry/motorcycle-license-plate).

---

### A5. Roboflow — "greenParking" (thaiphung)

| Mục | Nội dung |
|---|---|
| URL / host | [universe.roboflow.com/thaiphung/greenparking](https://universe.roboflow.com/thaiphung/greenparking) — Roboflow Universe |
| Size | 1.748 ảnh, publish 10/2023, 420 views / 25 downloads |
| Classes / format | 1 class (chỉ có id "0", không đặt tên) — object detection |
| License | CC BY 4.0 |
| Plate types / bối cảnh | Trang không có mô tả; các dự án "tương tự" được gợi ý có tên liên quan đến biển số Việt Nam ("bien_so_xe") nhưng bản thân trang này không xác nhận là bãi xe hay biển số. Tên gọi "GreenParking" trùng với từ khóa tìm kiếm ban đầu nhưng không đủ căn cứ để kết luận đây là dữ liệu liên quan trực tiếp |
| Đánh giá | Xác nhận dataset tồn tại thật, nhưng chưa đủ thông tin để xác định có liên quan đến bài toán biển số/bãi xe Việt Nam hay không — không khuyến nghị dùng làm nguồn chính, chỉ ghi nhận đã kiểm tra |

Nguồn: [r.jina.ai render 2026-07-30](https://r.jina.ai/https://universe.roboflow.com/thaiphung/greenparking).

---

### A6. Roboflow — "Viet Nam OCR plate" (license-plate-reg)

| Mục | Nội dung |
|---|---|
| URL / host | [universe.roboflow.com/license-plate-reg/viet-nam-ocr-plate](https://universe.roboflow.com/license-plate-reg/viet-nam-ocr-plate) — Roboflow Universe |
| Size | 3.819 ảnh, publish ~3/2025 |
| Classes / format | 32 class ký tự (chữ số, chữ cái, "words"...) — theo kiểu OCR-as-detection, mỗi ký tự là một class riêng; gần nhất với có OCR ground truth trong nhóm dataset Roboflow Việt Nam đã khảo sát. Cách tiếp cận này tương tự phương pháp YOLOv8-nano OCR-as-detection của Tran & Bui 2025 (đã ghi ở note `2026-07-19-similar-parking-systems.md`, mục A1.1) |
| License | Public Domain — CC0 1.0 |
| Plate types | Không xác định được tỷ lệ 1 hàng/2 hàng qua trang, cần xem mẫu |
| Lighting/bối cảnh | Không có mô tả |
| Đánh giá | Lựa chọn phù hợp nhất nếu cần ground truth cấp ký tự thay vì chỉ bounding box biển, license CC0 dễ sử dụng |

Nguồn: [r.jina.ai render 2026-07-30](https://r.jina.ai/https://universe.roboflow.com/license-plate-reg/viet-nam-ocr-plate).

---

### A7. Kaggle — "VNLicensePlate_yolov7" (bomaich)

| Mục | Nội dung |
|---|---|
| URL / host | [kaggle.com/datasets/bomaich/vnlicenseplate](https://www.kaggle.com/datasets/bomaich/vnlicenseplate) — Kaggle |
| Size | 1.000 ảnh, đã chia sẵn train/valid/test, 996 file, 249 MB |
| Classes / format | Nhãn dạng `xywh` (txt) cho YOLOv7 — chỉ detect vùng biển, không OCR ground truth |
| License | "Unknown" |
| Plate types | Ghi nhận có "cả biển 1 hàng và 2 hàng" nhưng không tách số lượng cụ thể như A1 |
| Lighting/bối cảnh | Không có mô tả |
| Đánh giá | Cỡ mẫu nhỏ, giá trị chủ yếu ở việc đã có sẵn split train/valid/test để tham khảo định dạng, không phải nguồn ảnh chính |

Nguồn: [r.jina.ai render 2026-07-30](https://r.jina.ai/https://www.kaggle.com/datasets/bomaich/vnlicenseplate).

---

## B. Bộ dữ liệu phương tiện (car/motorbike/truck) bối cảnh đường phố/bãi xe Việt Nam

### B1. Roboflow — "Vietnamese vehicle" (Car classification, v3)

| Mục | Nội dung |
|---|---|
| URL / host | [universe.roboflow.com/car-classification/vietnamese-vehicle/dataset/3](https://universe.roboflow.com/car-classification/vietnamese-vehicle/dataset/3) — Roboflow Universe |
| Size | 1.547 ảnh, split 80/10/10 (1.235/156/156), publish 2/2023 |
| Classes | Mô tả tìm được qua WebSearch cho biết ban đầu là 4 lớp car/bus/truck/motorcycle, nhưng bản v3 hiện ghi "8 remapped classes" sau bước tiền xử lý — chưa xác định được danh sách 8 lớp cụ thể |
| License | CC BY 4.0 |
| Lighting/bối cảnh | Không có mô tả định lượng về ánh sáng/thời tiết |
| Đánh giá | Cỡ mẫu nhỏ (1.547 ảnh); cần xác minh lại danh sách 8 class trước khi sử dụng |

Nguồn: [r.jina.ai render 2026-07-30](https://r.jina.ai/https://universe.roboflow.com/car-classification/vietnamese-vehicle/dataset/3).

---

### B2. Roboflow — "Vehicle Vietnam-CanTho"

| Mục | Nội dung |
|---|---|
| URL / host | [universe.roboflow.com/vehicle/vehicle-vietnam-cantho-2gxc8](https://universe.roboflow.com/vehicle/vehicle-vietnam-cantho-2gxc8) — Roboflow Universe |
| Size | 1.110 ảnh (phiên bản hiện tại; 1.746 ảnh nếu tính gộp mọi phiên bản), publish ~2022 |
| Classes | 4 lớp: Car, Truck, Bus, Motorbike |
| License | CC BY 4.0 |
| Lighting/bối cảnh | Ảnh mẫu là cảnh đường phố ban ngày tại Cần Thơ, không có ảnh đêm theo mô tả trang |
| Đánh giá | 4 class đúng nhu cầu phân loại xe của đề tài, nhưng chỉ có bối cảnh ban ngày — chưa đáp ứng yêu cầu đa dạng ánh sáng cho camera cổng bãi xe |

Nguồn: [r.jina.ai render 2026-07-30](https://r.jina.ai/https://universe.roboflow.com/vehicle/vehicle-vietnam-cantho-2gxc8).

---

### B3. UIT-CVID21 (UIT-Together Research Group) — liên kết nguồn không truy cập được

| Mục | Nội dung |
|---|---|
| URL / host | Trang liệt kê: [uit-together.github.io/datasets/](https://uit-together.github.io/datasets/), trỏ tới `github.com/nguyenvd-uit/uit-together-dataset/blob/main/UIT-CVID21.md` — repo này trả về lỗi 404 khi truy cập ngày 2026-07-30 (đã thử cả file .md cụ thể và trang gốc repo) |
| Size / classes (theo mô tả gián tiếp, chưa xác minh trực tiếp) | 10.000 ảnh, 4 class (Bus, Car, Truck, Van), chụp từ drone/UAV trên đường Việt Nam |
| License | Không xác định được do không truy cập được trang nguồn |
| Lighting/bối cảnh | Góc chụp từ trên cao (drone), khác với góc camera cổng bãi xe ngang tầm mắt cần dùng trong đề tài |
| Đánh giá | Đúng là dataset do nhóm nghiên cứu tại UIT công bố như đề bài gợi ý, nhưng kho dữ liệu hiện không truy cập được (tương tự tình trạng dataset MAPR 2018 đã ghi ở note `2026-07-19-similar-parking-systems.md`, mục A1.5) — chỉ ghi nhận để tham khảo, chưa sử dụng được cho tới khi xác minh lại liên kết |

Nguồn (404): [github.com/nguyenvd-uit/uit-together-dataset](https://github.com/nguyenvd-uit/uit-together-dataset) và [.../blob/main/UIT-CVID21.md](https://github.com/nguyenvd-uit/uit-together-dataset/blob/main/UIT-CVID21.md), truy cập 2026-07-30.

---

### B4. GitHub — QuangTranUTE/Vehicle-Detection

| Mục | Nội dung |
|---|---|
| URL / host | [github.com/QuangTranUTE/Vehicle-Detection](https://github.com/QuangTranUTE/Vehicle-Detection) |
| Size | ~11.000 ảnh HD (1280×720) từ camera giám sát giao thông Việt Nam, có nguồn gốc từ cuộc thi AI 2020 (ai.icti-hcm.gov.vn); tập test 1.276 ảnh |
| Classes/format | Không thấy liệt kê rõ danh sách lớp trong nội dung lấy được; model tham chiếu là SSD MobileNetV2 FPNLite |
| License | Không thấy file LICENSE trong nội dung lấy được — cần kiểm tra lại trực tiếp trên repo trước khi sử dụng |
| Lighting/bối cảnh | Camera giám sát giao thông đô thị Việt Nam — bối cảnh đường phố, không phải bãi xe |
| Đánh giá | Cỡ mẫu tương đối lớn (11.000 ảnh) và đúng nguồn gốc Việt Nam, nhưng license chưa xác nhận và dữ liệu train thực tế yêu cầu đăng nhập Google Drive nên chưa kiểm chứng được nội dung/số lớp chi tiết |

Nguồn: [WebFetch 2026-07-30](https://github.com/QuangTranUTE/Vehicle-Detection).

---

## C. Bộ dữ liệu ALPR/bãi xe quốc tế dùng làm đối chiếu/tiền huấn luyện

### C1. CCPD — Chinese City Parking Dataset

| Mục | Nội dung |
|---|---|
| Trích dẫn | Z. Xu, W. Yang, A. Meng, N. Lu, H. Huang, C. Ying, and L. Huang, "Towards End-to-End License Plate Detection and Recognition: A Large Dataset and Baseline," in *Proc. ECCV*, 2018, pp. 255–271. |
| URL / host | [github.com/detectRecog/CCPD](https://github.com/detectRecog/CCPD) · paper: [Springer](https://link.springer.com/chapter/10.1007/978-3-030-01261-8_16) |
| Size | Hơn 300.000 ảnh (CCPD-Base + 6 subset thử thách DB/Blur/FN/Rotate/Tilt/Challenge + CCPD-Green cho biển xe điện 8 ký tự); chi tiết cỡ mẫu theo split đã ghi ở note `2026-07-18-yolo-architecture.md` (290.316 ảnh theo Sonnara và cộng sự 2025, 200k/20k/20k train/val/test + 6 subset 50.316 ảnh) |
| Classes / format | Nhãn được mã hoá trong tên file (không có file nhãn riêng): tỷ lệ vùng biển, góc nghiêng, bbox, 4 tọa độ góc, chuỗi biển 7 ký tự (1 ký tự tỉnh Trung Quốc + 1 chữ + 5 ký tự chữ-số), độ sáng, độ mờ |
| License | MIT (xác nhận qua GitHub repo) |
| Plate types | Chỉ biển Trung Quốc — hệ ký tự và bố cục khác biển Việt Nam, không phù hợp OCR trực tiếp, nhưng hữu ích để tiền huấn luyện phần detect vùng biển số nói chung |
| Lighting/bối cảnh | Camera cố định tại bãi xe Bắc Kinh 2016–2018; theo Sonnara và cộng sự 2025 (đã xác minh ở note YOLO): 61,4% ban ngày / 38,6% ban đêm, xoay ±60° trong mặt phẳng, nghiêng ngoài mặt phẳng tới 45° — dataset có số liệu về đa dạng ánh sáng rõ ràng nhất trong toàn bộ khảo sát này |
| Đánh giá | Không dùng để huấn luyện OCR ký tự Việt Nam, nhưng là ứng viên phù hợp để tiền huấn luyện detector vùng biển số trước khi fine-tune trên dữ liệu Việt Nam, đặc biệt nhờ tỷ lệ đêm 38,6% đã được định lượng — bối cảnh bãi xe cũng khớp với use-case của đề tài |

Nguồn: [GitHub detectRecog/CCPD (WebFetch 2026-07-30)](https://github.com/detectRecog/CCPD); tỷ lệ ngày/đêm đối chiếu với note `2026-07-18-yolo-architecture.md` §A3.1 (Sonnara và cộng sự 2025, CC-BY, full text).

---

### C2. PKLot

| Mục | Nội dung |
|---|---|
| Trích dẫn | P. R. L. Almeida, L. S. Oliveira, A. S. Britto Jr., E. J. Silva Jr., and A. L. Koerich, "PKLot — A robust dataset for parking lot classification," *Expert Systems with Applications*, vol. 42, no. 11, pp. 4937–4949, 2015. |
| URL / host | Roboflow mirror: [public.roboflow.com/object-detection/pklot](https://public.roboflow.com/object-detection/pklot) · trang gốc: [web.inf.ufpr.br/luizoliveira/research-interests/pklot](https://web.inf.ufpr.br/luizoliveira/research-interests/pklot/) |
| Size | 12.417 ảnh gốc (12.416 theo bản Roboflow) chụp tại 2 bãi xe (UFPR04, UFPR05, PUCPR — 3 camera), ~695.899 ảnh patch ô đỗ đã cắt sẵn |
| Classes / format | 1 class ("spaces") occupied/vacant — bbox ô đỗ đã chuẩn hoá qua Roboflow |
| License | CC BY 4.0 (theo trang Roboflow mirror) |
| Plate types | Không có biển số — đây là dataset về occupancy, không phải ALPR |
| Lighting/bối cảnh | Bãi đỗ ngoài trời, nhiều kiểu thời tiết (nắng/nhiều mây/mưa); không có ảnh ban đêm — nhiều bài trích dẫn PKLot ghi nhận điều kiện ánh sáng không đủ để chụp ban đêm trong giai đoạn thu thập gốc |
| Đánh giá | Hữu ích cho phía occupancy/bối cảnh xe (Đức), nhưng thiếu hoàn toàn ảnh ban đêm — chưa đáp ứng yêu cầu camera cổng bãi xe hoạt động 24/7 |

Nguồn: [public.roboflow.com/object-detection/pklot (WebFetch 2026-07-30)](https://public.roboflow.com/object-detection/pklot); thông tin không có ảnh đêm — [WebSearch tổng hợp từ nhiều nguồn thứ cấp trích dẫn PKLot, 2026-07-30]. Đây là claim tổng hợp từ các bài trích dẫn, chưa đọc trực tiếp README gốc để xác nhận tuyệt đối — nên kiểm tra lại `pklot-readme.pdf` nếu cần trích dẫn số liệu này trong báo cáo chính thức.

---

### C3. CNRPark + CNRPark-EXT

| Mục | Nội dung |
|---|---|
| Trích dẫn | G. Amato, F. Carrara, F. Falchi, C. Gennaro, C. Meghini, and C. Vairo, "Deep learning for decentralized parking lot occupancy detection," *Expert Systems with Applications*, vol. 72, pp. 327–334, 2017. (Dataset gốc CNRPark: cùng nhóm tác giả trừ Meghini, ISCC 2016.) |
| URL / host | [cnrpark.it](http://cnrpark.it/) — WebFetch báo lỗi certificate khi truy cập trực tiếp domain này, nên thông tin dưới đây lấy từ trang paper/GitHub liên quan, không phải từ chính cnrpark.it |
| Size | CNRPark gốc: 12.000 ảnh (7/2015, 2 camera); CNRPark-EXT: 4.287 ảnh full-scene → 144.965–150.000 patch ô đỗ đã gán nhãn (11/2015–2/2016, 9 camera, 164 ô đỗ) |
| Classes / format | Nhị phân occupied/vacant, ảnh patch đã crop sẵn theo ô đỗ |
| License | Chưa xác minh được trực tiếp do lỗi certificate khi truy cập cnrpark.it — cần kiểm tra lại trang gốc trước khi sử dụng chính thức |
| Plate types | Không có biển số |
| Lighting/bối cảnh | Đa dạng nhất trong nhóm occupancy: 9 camera góc khác nhau, nhiều kiểu thời tiết, và có ảnh thiếu sáng/ban đêm — nguồn ghi nhận "CNRPark + EXT includes dark or night time patches" |
| Đánh giá | Dataset occupancy duy nhất trong khảo sát này xác nhận có dữ liệu ban đêm — bổ sung cho khoảng trống của PKLot, tuy license chưa xác minh được nên cần kiểm tra lại trước khi sử dụng chính thức |

Nguồn: [ScienceDirect Amato và cộng sự 2017](https://www.sciencedirect.com/science/article/abs/pii/S095741741630598X); thông tin về ảnh đêm — [tổng hợp WebSearch từ các bài trích dẫn CNRPark-EXT, 2026-07-30]; lỗi certificate khi truy cập `cnrpark.it` trực tiếp ngày 2026-07-30 — cần kiểm tra lại license trang chủ qua trình duyệt thông thường.

---

### C4. AOLP (Application-Oriented License Plate)

| Mục | Nội dung |
|---|---|
| Trích dẫn | G.-S. Hsu, J.-C. Chen, and Y.-Z. Chung, "Application-Oriented License Plate Recognition," *IEEE Trans. Vehicular Technology*, vol. 62, no. 2, pp. 552–561, 2013. |
| URL / host | Trang xin quyền truy cập: [sites.google.com/site/avlabaolp/download](https://sites.google.com/site/avlabaolp/download) |
| Size | 2.049 ảnh biển Đài Loan, chia 3 subset: Access Control (AC) 681, Law Enforcement (LE) 757, Road Patrol (RP) 611 |
| License | Miễn phí cho mục đích học thuật, cấm sử dụng thương mại; phải xin phép bằng văn bản từ Prof. Gee-Sern Hsu nếu chia sẻ cho người khác, cần mật khẩu để giải nén — không phải dữ liệu tải tự do |
| Plate types | Biển Đài Loan, khác định dạng và bố cục biển Việt Nam |
| Lighting/bối cảnh | 3 kịch bản camera khác nhau (kiểm soát ra vào, phạt nguội, tuần tra đường), nhưng không phải bối cảnh bãi xe Việt Nam |
| Đánh giá | Chỉ nên dùng làm số liệu so sánh ở phần tổng quan (đã dùng ở note `2026-07-19-similar-parking-systems.md`, mục A2.3, qua Al-batat 2022), không phải nguồn train trực tiếp do khác định dạng biển và thủ tục xin quyền phức tạp |

Nguồn: [AVLab-AOLP download page (WebSearch snippet trích nguyên văn điều khoản, 2026-07-30)](https://sites.google.com/site/avlabaolp/download).

---

### C5. OpenALPR benchmarks (EU/US/BR)

| Mục | Nội dung |
|---|---|
| URL / host | [github.com/openalpr/benchmarks](https://github.com/openalpr/benchmarks), thư mục `endtoend/{us,eu,br}` |
| Size | Theo Al-batat và cộng sự 2022 (đã xác minh full text ở note `2026-07-19-similar-parking-systems.md`, mục A2.3): OpenALPR EU 108 mẫu; theo WebSearch riêng trong phiên này, OpenALPR US ~222 ảnh |
| License | AGPL-3.0 (có file LICENSE trong repo, xác nhận qua WebFetch) |
| Plate types | Biển Mỹ/EU/Brazil — không phải biển Việt Nam |
| Lighting/bối cảnh | Chưa kiểm tra chi tiết vì không phải ứng viên chính |
| Đánh giá | Chỉ dùng làm benchmark đối chiếu quy mô nhỏ, không phải nguồn train — cỡ mẫu quá nhỏ, và AGPL-3.0 là license copyleft mạnh nên cần lưu ý nếu tái sử dụng code kèm theo |

Nguồn: [GitHub openalpr/benchmarks (WebFetch 2026-07-30)](https://github.com/openalpr/benchmarks).

---

## D. Bảng so sánh tổng hợp

| Dataset | Host | Size | Classes | License (đã kiểm tra) | Biển VN 1 hàng/2 hàng? | Ánh sáng | Bối cảnh |
|---|---|---|---|---|---|---|---|
| VN License Plate Segment (A1) | Kaggle | ~5.000 | 2 (1 hàng: 3.510 / 2 hàng: 1.625) | Unknown — cần xác minh | Có, tách rõ số lượng | Đa dạng (không định lượng) | Internet + thực tế |
| Cuong Ta VN Car Plate (A2) | Roboflow | 8.255 | 1 (plate, no OCR) | CC0 1.0 | Không rõ tỷ lệ | Đo qua EDA: TB 100,0, 13,7% tối | Cổng bãi xe (xác nhận qua EDA), đủ cả ô tô lẫn xe máy |
| school-fuhih VN plate (A3) | Roboflow | 8.397 | 1 (plate, no OCR) | CC BY 4.0 | Không rõ tỷ lệ | Không mô tả | Không rõ |
| Motorcycle plate — HaUI (A4) | Roboflow | 1.748 | 1 (plate, no OCR) | MIT | Thiên về xe máy (2 hàng), chưa rõ tỷ lệ | Không mô tả | Không rõ |
| greenParking (A5) | Roboflow | 1.748 | 1 (không đặt tên) | CC BY 4.0 | Không xác định được | Không mô tả | Không xác định được |
| Viet Nam OCR plate (A6) | Roboflow | 3.819 | 32 (ký tự — có OCR ground truth kiểu detect-per-char) | CC0 1.0 | Không rõ tỷ lệ | Không mô tả | Không rõ |
| VNLicensePlate_yolov7 (A7) | Kaggle | 1.000 | plate (1&2 hàng, không tách số) | Unknown — cần xác minh | Có (gộp) | Không mô tả | Không rõ |
| Vietnamese vehicle (B1) | Roboflow | 1.547 | 8 (cần xác minh lại danh sách) | CC BY 4.0 | N/A (vehicle, không phải plate) | Không mô tả | Đường phố |
| Vehicle Vietnam-CanTho (B2) | Roboflow | 1.110–1.746 | 4 (car/truck/bus/motorbike) | CC BY 4.0 | N/A | Chỉ ban ngày | Đường phố Cần Thơ |
| UIT-CVID21 (B3) | GitHub (UIT) | 10.000 (chưa xác minh trực tiếp) | 4 (bus/car/truck/van) | Không xác định — repo 404 | N/A | Góc drone, không phải góc bãi xe | Đường Việt Nam (trên cao) |
| QuangTranUTE Vehicle-Detection (B4) | GitHub | ~11.000 | Không rõ | Không xác định | N/A | Không mô tả | Camera giám sát giao thông Việt Nam |
| CCPD (C1) | GitHub | >300.000 | Detect + OCR (biển Trung Quốc) | MIT | Không — biển Trung Quốc | 61,4% ngày / 38,6% đêm (định lượng) | Bãi xe Trung Quốc |
| PKLot (C2) | Roboflow mirror | 12.416–12.417 (+695k patch) | occupied/vacant | CC BY 4.0 | N/A | Đa thời tiết, không có đêm | Bãi xe ngoài trời (Brazil) |
| CNRPark(+EXT) (C3) | cnrpark.it | 12.000 + ~145–150k patch | occupied/vacant | Chưa xác minh được (lỗi cert khi truy cập) | N/A | Đa thời tiết + có ảnh đêm/thiếu sáng | Bãi xe ngoài trời (Ý) |
| AOLP (C4) | Xin quyền qua form | 2.049 | plate (biển Đài Loan) | Học thuật only, cấm thương mại, cần xin phép bằng văn bản | Không — biển Đài Loan | 3 kịch bản góc chụp khác nhau | Kiểm soát ra vào / phạt nguội / tuần tra |
| OpenALPR benchmarks (C5) | GitHub | EU 108 / US ~222 | plate US/EU/BR | AGPL-3.0 | Không | Không kiểm tra | Đối chiếu quy mô nhỏ |

---

## E. Khuyến nghị

Không có dataset công khai đơn lẻ nào trong số 16 bộ trên vừa có biển Việt Nam tách 1 hàng/2 hàng, vừa có ánh sáng đa dạng được định lượng, vừa đúng bối cảnh bãi xe/cổng vào cùng lúc. Cần phối hợp nhiều nguồn:

1. **Biển số detection (Nhật):** dùng A1 (Kaggle, `duydieunguyen/licenseplates`) làm nguồn chính vì là dataset duy nhất tách rõ số lượng biển 1 hàng (3.510)/2 hàng (1.625), kết hợp thêm A2 hoặc A3 (Roboflow, CC0/CC BY, ~8.000 ảnh) để tăng cỡ mẫu biển ô tô, và A4 (HaUI motorcycle, MIT) để tăng tỷ trọng biển xe máy 2 hàng. Trước khi sử dụng A1 trong báo cáo/công bố chính thức, cần liên hệ tác giả Kaggle xác nhận điều khoản sử dụng vì license hiện ghi "Unknown".
2. **OCR ground truth (Nhật):** nếu cần ground truth cấp ký tự thay vì chỉ bbox biển, A6 (Viet Nam OCR plate, CC0) là lựa chọn khả dụng duy nhất tìm được có annotation kiểu ký tự, dù cỡ mẫu nhỏ hơn (3.819 ảnh) và chưa xác nhận được số lượng chuỗi biển hợp lệ đầy đủ.
3. **Pretrain detector biển số nói chung (Nhật, tùy chọn):** CCPD (C1, MIT) không dùng để huấn luyện ký tự Việt Nam được, nhưng transfer learning phần detect vùng hình chữ nhật biển số trước khi fine-tune trên dữ liệu Việt Nam có thể cải thiện recall, đặc biệt nhờ tỷ lệ đêm 38,6% đã được định lượng.
4. **Phân loại xe/bối cảnh bãi xe (Đức):** B2 (Vehicle Vietnam-CanTho, CC BY 4.0) cho 4 lớp car/truck/bus/motorbike đúng bối cảnh đường phố Việt Nam, kết hợp C3 (CNRPark+EXT) cho phần occupancy có dữ liệu ban đêm (license của C3 chưa xác minh được, cần kiểm tra `cnrpark.it` qua trình duyệt thông thường).
5. Không khuyến nghị dùng B3 (UIT-CVID21, liên kết không truy cập được), C4 (AOLP, thủ tục xin quyền phức tạp và khác định dạng biển), C5 (OpenALPR, cỡ mẫu quá nhỏ) làm nguồn ảnh chính — chỉ giữ giá trị tham khảo/so sánh.

---

## F. Gap analysis — điều kiện không được dataset công khai nào bao phủ đầy đủ

- Không có dataset biển số Việt Nam nào (A1–A7) định lượng rõ tỷ lệ ảnh ngày/đêm hoặc trong nhà/ngoài trời — toàn bộ trang Roboflow/Kaggle đã khảo sát đều thiếu mô tả ánh sáng chi tiết. Đây là khoảng trống lớn nhất, liên quan trực tiếp đến use-case camera cổng bãi xe của đề tài, vì camera thực tế sẽ hoạt động cả ban đêm và có thể đặt trong nhà xe có mái che (đèn vàng/đèn huỳnh quang, khác quang phổ ánh sáng ban ngày).
- Không có dataset nào mô phỏng đúng bối cảnh cổng bãi xe có mái/gờ chắn, góc camera cố định ngang tầm mắt hướng vào xe đi qua — B2 là ảnh đường phố góc rộng, C1 (CCPD) là bãi xe nhưng biển Trung Quốc, C2/C3 là ảnh full-scene bãi xe nhưng nhắm vào occupancy chứ không phải cận cảnh biển số xe đi qua cổng.
- Không có dataset nào xác nhận có ảnh biển số dưới điều kiện mưa/sương mù/ngược sáng (đèn pha ban đêm chiếu thẳng camera) — đây là điều kiện thực tế phổ biến tại cổng bãi xe Việt Nam nhưng không tìm thấy dataset công khai nào có số liệu về việc này.
- Từ các khoảng trống trên, nhóm cần tự chụp bổ sung tối thiểu các điều kiện: (a) ban đêm dùng đèn cổng/đèn pha thực tế, (b) trong nhà xe có mái che ánh sáng nhân tạo, (c) góc camera cố định đúng độ cao/góc nghiêng dự kiến lắp đặt trên Raspberry Pi 5, (d) biển số 2 hàng xe máy cận cảnh đúng khoảng cách chụp thực tế (dataset công khai đa số là ảnh xa hoặc góc giám sát chung).

*(Cập nhật: sau khi tải dữ liệu thực tế và xem ảnh mẫu — xem mục H bên dưới — hai gạch đầu dòng đầu tiên ở trên chỉ đúng một phần.)*

---

## G. Lưu ý quyền riêng tư khi tự chụp bổ sung (Luật Bảo vệ dữ liệu cá nhân, hiệu lực 01/01/2026)

Phần này chỉ nêu nguyên tắc chung đã được xác lập sẵn trong CLAUDE.md của dự án, không tự suy diễn thêm chi tiết pháp lý cụ thể (số điều khoản, mức phạt, thủ tục hành chính chính xác) do chưa có nguồn văn bản luật được xác minh trực tiếp trong phiên này. Các chi tiết pháp lý cụ thể dưới đây cần nhóm xác minh lại với giảng viên hướng dẫn/cơ sở đào tạo trước khi thực hiện, không dùng note này làm căn cứ pháp lý cuối cùng.

Biển số xe và ảnh phương tiện được xem là dữ liệu cá nhân theo luật này (đã ghi nhận trong CLAUDE.md của dự án). Khi tự chụp bổ sung, nhóm cần tuân thủ các nguyên tắc sau:

- Kiểm soát truy cập: ảnh/video thô lưu trữ có kiểm soát quyền truy cập (không công khai trong repo Git hay ổ đĩa chia sẻ không giới hạn), chỉ thành viên nhóm/giảng viên hướng dẫn có quyền xem.
- Retention/xóa dữ liệu: đặt thời hạn lưu trữ rõ ràng cho ảnh tự chụp phục vụ nghiên cứu, không giữ vô thời hạn sau khi đề tài kết thúc, tự động/thủ công xóa sau thời hạn.
- Tránh chụp người ngoài cuộc: khi chụp thử nghiệm tại bãi xe/cổng thực tế, hạn chế tối đa việc lọt khuôn mặt người đi đường hoặc người ngồi trong xe không liên quan đến nghiên cứu; ưu tiên góc chụp chỉ lấy vùng xe và biển số.
- Làm mờ/loại trừ biển số bên thứ ba: nếu ảnh chụp vô tình lọt biển số xe khác không thuộc phạm vi nghiên cứu, cần làm mờ hoặc crop loại bỏ trước khi sử dụng/lưu trữ lâu dài.
- Thông báo/xin phép tại điểm chụp (nếu áp dụng): nếu chụp tại bãi xe của bên thứ ba (không phải cơ sở của trường), cần có sự đồng ý/thông báo với đơn vị quản lý bãi xe trước khi lắp camera thử nghiệm.

Cần xác minh với giảng viên/cơ sở đào tạo: phạm vi chính xác của khái niệm "dữ liệu cá nhân" áp dụng cho biển số theo luật (biển số cá nhân sở hữu so với biển số công ty/tổ chức có thể có quy chế khác), thủ tục xin phép cụ thể nếu có (nếu bãi xe thuộc trường thì cần liên hệ phòng quản lý cơ sở vật chất), và mức độ ẩn danh hoá cần thiết trước khi đưa ảnh vào báo cáo/slide/video demo công khai.

---

## H. Bổ sung 2026-07-30 (sau khi tải dữ liệu thực tế và xem ảnh mẫu qua EDA)

Nhóm đã tải và chạy EDA thực tế (notebook `src/ml/notebooks/eda-plate-datasets.ipynb`, số liệu tại `docs/research/eda_outputs/eda_summary.csv`, hình tại `docs/report/figures/eda_*.png`) cho 4 dataset: A1 (VN License Plate Segment, Kaggle), A2 (Cuong Ta), A3 (school-fuhih), A4 (HaUI motorcycle) — A3/A4/A1 là nền chính đã chốt cho Tuần 2, A1/A2 thêm vào sau vì là top 2 ưu tiên cho riêng bài toán detect vùng biển số (xem mục A). Kết quả điều chỉnh lại nhận định ở mục F phía trên:

- Cả 4 dataset thực chất đều là ảnh chụp từ camera cổng bãi xe/hầm gửi xe có thanh chắn (boom barrier) — không phải ảnh đường phố chung chung như suy đoán ban đầu dựa trên mô tả text trên trang nguồn. Ảnh mẫu (`eda_sample_context.png`) cho thấy cả 4 dataset đều có khung hình cận cảnh đầu xe/biển số ngay tại cổng, nhiều ảnh có thanh chắn màu vàng-đen trong khung hình, và một số ảnh A2/A3 chụp trong hầm/nhà xe thiếu sáng. Ảnh còn có timestamp cháy vào góc theo định dạng camera an ninh DVR (ví dụ `12/09/2016 09:09:23`, `06/12/2017`), cho thấy đây là dữ liệu thực tế từ camera giám sát cổng bãi xe, không phải ảnh thu thập ngẫu nhiên. A2 (Cuong Ta) còn xác nhận đúng nhận xét ban đầu: có cả ô tô (Toyota, Nissan, Kia) lẫn xe máy, và A1 xuất hiện cả xe tải trong ảnh mẫu.
- Nhận định ở mục F ("không dataset nào mô phỏng đúng bối cảnh cổng bãi xe") chỉ đúng khi chỉ dựa vào mô tả text công khai trên trang Roboflow/Kaggle — đây là giới hạn của khảo sát ban đầu. Khi xem trực tiếp nội dung ảnh thì nhận định này không còn đúng. Bài học rút ra: đối với dataset không có mô tả, cần tải và xem mẫu ảnh thực tế mới đánh giá được bối cảnh chính xác, không nên kết luận "thiếu mô tả nên không phù hợp" như đã viết ban đầu.
- Khoảng trống về ánh sáng ban đêm định lượng vẫn đúng một phần: EDA đo được bằng độ sáng trung bình ảnh xám (chỉ là proxy, không phải nhãn ngày/đêm thật) — A4 gần như không có biến thiên ánh sáng (dải hẹp, độ lệch chuẩn thấp), A1/A2/A3 đều chỉ khoảng 11–14% ảnh rơi vào mức "tối/thiếu sáng" (A2: 13,7%, A3: 12,8%, A1: 10,7%). Nhóm vẫn cần tự chụp bổ sung nếu muốn có tỷ lệ đêm cao hơn và đa dạng hơn (mưa, ngược sáng đèn pha) như đã nêu ở mục F.
- Phát hiện thêm ngoài dự kiến: ảnh xuất từ Roboflow của A3 (school-fuhih) và A4 (HaUI) bị resize cố định về một kích thước duy nhất (640×640 cho A3, 472×303 cho A4) trong bước tiền xử lý export, làm mất hoàn toàn đa dạng độ phân giải gốc. Nhưng A2 (Cuong Ta), dù cũng export từ Roboflow, lại KHÔNG bị resize (240–2000 × 160–1500 px, có std ≠ 0) — nên không phải cứ export từ Roboflow là bị resize, tùy từng dataset/tùy cấu hình lúc tác giả tạo phiên bản export. Cùng với A1 (Kaggle, 380–4032px), A2 là dataset thứ hai giữ được độ phân giải gốc đa dạng. Khi tự chụp bổ sung, cần giữ ảnh gốc độ phân giải cao và chỉ resize ở bước tiền xử lý huấn luyện, không phụ thuộc vào bản export có thể đã bị hạ giải.
