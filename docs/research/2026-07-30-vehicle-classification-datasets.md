# Khảo sát bộ dữ liệu công khai: phân loại kiểu dáng phương tiện (vehicle body-type classification)

**Ngày tạo:** 2026-07-30 · **Mode:** 3 (dataset research)
**Mục đích:** phục vụ Tuần 5 — nhánh phân loại xe (Nhật): xe con theo kiểu dáng (sedan, SUV, hatchback, MPV/minivan), pickup truck, xe tải (truck), xe máy (motorbike), có thể cả van/xe khách. Đây là khảo sát bổ sung cho note `docs/research/2026-07-30-parking-vehicle-plate-datasets.md` (note đó đã khảo sát biển số VN + phương tiện bối cảnh VN nhưng chỉ ở mức 1-class "car/truck/bus/motorbike", chưa đi sâu vào kiểu dáng xe con) — không lặp lại nội dung phần A/C của note đó, chỉ tham chiếu chéo phần B khi cần.

---

## A. Bộ dữ liệu kiểu dáng xe con (car body-type) — không có xe máy

### A1. Roboflow — "Vehicle Body Style Dataset" (Research Projects) — dataset đã chọn

| Mục | Nội dung |
|---|---|
| URL / host | [universe.roboflow.com/research-projects-qodgb/vehicle-body-style-dataset](https://universe.roboflow.com/research-projects-qodgb/vehicle-body-style-dataset) — Roboflow Universe |
| Size | 10.000 ảnh, publish ước tính ~11/2022 (trang ghi "Updated 2 years ago" tính từ lúc kiểm tra) |
| Classes / format | 12 class: SUV, Minibus, Sedan, Convertible, Crossover, Fastback, Hardtop Convertible, Hatchback, MPV, Pickup Truck, Sports, Wagon — đúng 12 kiểu dáng của CompCars (A3), có vẻ dataset này được xây dựng/gán nhãn lại từ ảnh CompCars hoặc theo cùng cách phân loại; object detection (bounding box), không chỉ classification |
| License | CC BY 4.0 |
| Xe máy | Không có |
| Đánh giá | Cỡ vừa (10.000 ảnh), license CC BY dễ dùng hơn CompCars gốc, và có sẵn bounding box thay vì chỉ ảnh crop theo class — hữu ích nếu cần localize xe theo kiểu dáng trong khung hình rộng |

Nguồn: [r.jina.ai render 2026-07-30](https://r.jina.ai/https://universe.roboflow.com/research-projects-qodgb/vehicle-body-style-dataset).

---

### A2. Stanford Cars (Cars196)

| Mục | Nội dung |
|---|---|
| URL / host | Trang gốc [ai.stanford.edu/~jkrause/cars/car_dataset.html](http://ai.stanford.edu/~jkrause/cars/car_dataset.html) — 404 ngày 2026-07-30; mirror chính thức [TensorFlow Datasets `cars196`](https://www.tensorflow.org/datasets/catalog/cars196); cũng có trên Kaggle/HuggingFace |
| Trích dẫn | J. Krause, M. Stark, J. Deng, and L. Fei-Fei, "3D Object Representations for Fine-Grained Categorization," in *4th Int. IEEE Workshop on 3D Representation and Recognition (3dRR-13)*, 2013. |
| Size | 16.185 ảnh, 196 class, chia 8.144 train / 8.041 test (~50/50 mỗi class) |
| Classes / format | 196 class ở mức Make + Model + Year (vd "2012 Tesla Model S"), không có nhãn kiểu dáng (body-type) chính thức từ tác giả gốc — annotation classification + bounding box |
| License | Các nguồn không khớp nhau: trang TFDS ghi "CC BY 4.0" (nhãn generic của catalog TFDS, chưa chắc đúng điều khoản gốc của Stanford); trang gốc Stanford — nơi ghi điều khoản thật — hiện không mở được để đối chiếu, nên coi là chưa xác minh chắc chắn, không dùng làm căn cứ license cuối cùng |
| Kiểu dáng xe con | Không có nhãn gốc; có thể suy ra gián tiếp bằng cách nhóm 196 class theo tên (vd "Sedan", "SUV", "Hatchback", "Coupe", "Convertible", "Wagon", "Van", "Cab" xuất hiện trong tên class) — cách này một số nghiên cứu phụ (vd MaskCon, arXiv 2303.12756) và một dataset phái sinh trên Kaggle (xem A5) đã làm, không phải nhãn chính thức |
| Xe máy | Không có |
| Đánh giá | Ảnh chất lượng cao, đa dạng góc chụp/nền, nhưng không phải dataset kiểu dáng xe đúng nghĩa — chỉ dùng được sau khi tự map 196 class về nhóm kiểu dáng, khá tốn công và không chính thức; license chưa rõ ràng cũng là điểm trừ |

Nguồn: [TFDS cars196 (WebFetch 2026-07-30)](https://www.tensorflow.org/datasets/catalog/cars196); 404 trực tiếp tại [ai.stanford.edu/~jkrause/cars/car_dataset.html](http://ai.stanford.edu/~jkrause/cars/car_dataset.html); tình trạng server offline từ 2023 — [GitHub issue KaiyangZhou/CoOp #61 (WebSearch snippet 2026-07-30)](https://github.com/KaiyangZhou/CoOp/issues/61).

---

### A3. CompCars (Comprehensive Cars)

| Mục | Nội dung |
|---|---|
| URL / host | [mmlab.ie.cuhk.edu.hk/datasets/comp_cars](https://mmlab.ie.cuhk.edu.hk/datasets/comp_cars/) — trang chính thức CUHK MMLab |
| Trích dẫn | L. Yang, P. Luo, C. C. Loy, and X. Tang, "A Large-Scale Car Dataset for Fine-Grained Categorization and Verification," in *Proc. CVPR*, 2015. |
| Size | Web-nature: 136.726 ảnh xe đầy đủ + 27.618 ảnh bộ phận xe (163 hãng, 1.716 model); Surveillance-nature: 50.000 ảnh chụp từ camera giám sát góc trước |
| Classes / format | 12 kiểu dáng xe định nghĩa rõ: MPV, SUV, hatchback, sedan, minibus, fastback, estate, pickup, sports, crossover, convertible, hardtop convertible — mỗi model được gán 1 trong 12 nhãn này cùng 4 thuộc tính khác (tốc độ tối đa, dung tích xy-lanh, số cửa, số ghế); có bbox + góc nhìn (viewpoint) cho phần web-nature |
| License | Chỉ dùng cho nghiên cứu phi thương mại ("available for non-commercial research purposes only"); cấm sao chép/xuất bản/phân phối lại (trừ dùng nội bộ một tổ chức); phải trích dẫn paper CVPR 2015 khi dùng |
| Xe máy | Không có (chỉ xe con — không có xe tải hạng nặng, xe buýt lớn, hay xe máy) |
| Đánh giá | Nguồn tốt nhất tìm được cho danh sách kiểu dáng xe con chi tiết (12 lớp, có sedan/SUV/hatchback/MPV/pickup ), nhưng license phi thương mại chặt hơn CC BY, và phải làm thủ tục xin quyền tải |

Nguồn: [mmlab.ie.cuhk.edu.hk/datasets/comp_cars (WebFetch 2026-07-30)](https://mmlab.ie.cuhk.edu.hk/datasets/comp_cars/).

---

### A4. VMMRdb (Vehicle Make and Model Recognition dataset)

| Mục | Nội dung |
|---|---|
| URL / host | [github.com/faezetta/VMMRdb](https://github.com/faezetta/VMMRdb) (repo gốc); mirror [github.com/lgov/VMMRdb](https://github.com/lgov/VMMRdb); cũng có trên Kaggle |
| Trích dẫn | F. Tafazzoli, H. Frigui, and K. Nishiyama, "A Large and Diverse Dataset for Improved Vehicle Make and Model Recognition," in *Proc. CVPR Workshops*, 2017. |
| Size | 291.752 ảnh, 9.170 class (make+model+year, xe sản xuất 1950–2016, từ 712 khu vực địa lý) |
| Classes / format | Chỉ có nhãn make/model/year — không có nhãn kiểu dáng (body-type) trong mô tả gốc |
| License | MIT (có file LICENSE trong repo, xác nhận qua WebFetch, dù không đọc được toàn văn nội dung trong phiên này) |
| Xe máy | Không có |
| Đánh giá | Cỡ rất lớn, license dễ dùng nhất (MIT) trong nhóm A, nhưng không giúp trực tiếp cho bài toán phân loại kiểu dáng vì không có nhãn sedan/SUV/v.v. — chỉ dùng được nếu tự map model→kiểu dáng (tốn công như A2), không khuyến nghị làm nguồn chính cho việc này |

Nguồn: [github.com/faezetta/VMMRdb (WebFetch 2026-07-30)](https://github.com/faezetta/VMMRdb).

---

### A5. Kaggle — "Stanford Car Body Type Data" (mayurmahurkar)

| Mục | Nội dung |
|---|---|
| URL / host | [kaggle.com/datasets/mayurmahurkar/stanford-car-body-type-data](https://www.kaggle.com/datasets/mayurmahurkar/stanford-car-body-type-data) — Kaggle |
| Size | 8.146 file (~996 MB), chỉ dùng phần train của Stanford Cars gốc (A2) |
| Classes / format | Bản gán nhãn lại thủ công của tác giả Kaggle từ tên class gốc Stanford Cars — trích "hatchback, sedan, SUV, v.v." từ tên 196 class; có thư mục "Other" gộp các model SuperCab; kèm file `stanford_cars_type.csv` map tên file gốc → hãng xe + kiểu dáng |
| License | Ghi "Other (specified in description)" trên Kaggle — không phải license chuẩn, cần đọc mô tả gốc để biết chi tiết, chưa xác minh được cụ thể trong phiên này |
| Xe máy | Không có |
| Đánh giá | Là bằng chứng cho thấy Stanford Cars có thể dùng cho bài toán kiểu dáng nếu chấp nhận nhãn gán lại phi chính thức (không phải nhãn gốc Stanford công bố) — nhưng license "Other" mơ hồ và việc gán nhãn lại chưa qua peer-review nên độ chính xác nhãn không đảm bảo |

Nguồn: [r.jina.ai render 2026-07-30](https://r.jina.ai/https://www.kaggle.com/datasets/mayurmahurkar/stanford-car-body-type-data).

---

### A6. Kaggle/Mendeley — VTID2 (Vehicle Type Image Dataset, v2)

| Mục | Nội dung |
|---|---|
| URL / host | Nguồn chính thức: [data.mendeley.com/datasets/htsngg9tpc/3](https://data.mendeley.com/datasets/htsngg9tpc/3) (Mendeley Data, DOI `10.17632/htsngg9tpc.3`); mirror Kaggle: [kaggle.com/datasets/sujaykapadnis/vehicle-type-image-dataset](https://www.kaggle.com/datasets/sujaykapadnis/vehicle-type-image-dataset) |
| Trích dẫn | N. Boonsirisumpun and O. Surinta, "Vehicle image datasets for image classification," *Data in Brief*, vol. 53, 110133, 2024 (paper mô tả VTID1+VTID2); dataset publish 29/11/2023, tác giả ở Mahasarakham University |
| Size | 4.356 ảnh theo trang Mendeley chính thức (bản Kaggle mirror ghi 4.793 file — chênh nhau chút, có thể do khác version hoặc file phụ, chưa xác định rõ nguyên nhân) |
| Classes / format | 5 class: Sedan (1.230), Pick-up (1.240), SUV (680), Hatchback (606), Other (600) — classification theo thư mục, không phải detection |
| License | CC BY 4.0 (ghi rõ trên trang Mendeley chính thức) |
| Xe máy | Không có |
| Đánh giá | Dataset classification thuần (không phải detect-and-crop) với 4 kiểu dáng xe con cụ thể + 1 lớp "Other", license CC BY 4.0 rõ nhất trong nhóm A, có bài báo Data in Brief mô tả cách thu thập — hợp làm classification head riêng nếu pipeline tách detect (YOLO) → classify (kiểu dáng) thành 2 bước |

Nguồn: [data.mendeley.com/datasets/htsngg9tpc/3 (WebFetch 2026-07-30)](https://data.mendeley.com/datasets/htsngg9tpc/3); mirror Kaggle — [r.jina.ai render 2026-07-30](https://r.jina.ai/https://www.kaggle.com/datasets/sujaykapadnis/vehicle-type-image-dataset).

---

## B. Bộ dữ liệu đa lớp từ camera giao thông (có truck/bus/pickup, một số có xe máy)

### B1. BIT-Vehicle

| Mục | Nội dung |
|---|---|
| URL / host | Trang tải chính thức `iitlab.bit.edu.cn/mcislab/vehicledb/startRequestDb.php` — lỗi DNS ngày 2026-07-30 (`ENOTFOUND`), có thể domain đã đổi/ngừng; thông tin dưới đây lấy từ paper gốc + trích dẫn thứ cấp |
| Trích dẫn | Z. Dong, Y. Wu, M. Pei, and Y. Jia, "Vehicle Type Classification Using a Semisupervised Convolutional Neural Network," *IEEE Trans. Intelligent Transportation Systems*, vol. 16, no. 4, pp. 2247–2256, 2015. |
| Size | 9.850 ảnh (một số nguồn thứ cấp trích tập con 900 ảnh dùng thử nghiệm ban đầu); ảnh 1600×1200 hoặc 1920×1080 |
| Classes / format | 6 class: Bus (558), Microbus (883), Minivan (476), Sedan (5.922), SUV (1.392), Truck (822) — classification + bbox (annotation MATLAB) |
| License | Chưa xác minh được trực tiếp — trang tải chính thức không mở được trong phiên này; cần nhóm tự thử lại hoặc tìm domain thay thế |
| Xe máy | Không có |
| Đánh giá | Danh sách 6 class khá hợp yêu cầu (có sedan/SUV/truck/minivan/microbus/bus), cỡ vừa phải, camera giám sát góc trước gần giống use-case cổng bãi xe — nhưng link tải chính thức hiện không mở được và license chưa xác minh, cần nhóm tự dò lại nguồn (liên hệ tác giả hoặc mirror GitHub bên thứ ba) |

Nguồn: paper DOI xác nhận qua WebSearch; lỗi DNS khi mở trực tiếp `iitlab.bit.edu.cn` ngày 2026-07-30.

---

### B2. MIO-TCD (Traffic Camera Dataset)

| Mục | Nội dung |
|---|---|
| URL / host | [tcd.miovision.com/challenge/dataset.html](https://tcd.miovision.com/challenge/dataset.html) — trang chính thức Miovision |
| Trích dẫn | Z. Luo, F. Branchaud-Charron, C. Lemaire, J. Konrad, S. Li, A. Mishra, A. Achkar, J. Eichel, and P.-M. Jodoin, "MIO-TCD: A New Benchmark Dataset for Vehicle Classification and Localization," *IEEE Trans. Image Processing*, vol. 27, no. 10, pp. 5129–5141, 2018. |
| Size | 786.702 ảnh tổng cộng: 648.959 ảnh classification (crop theo object) + 137.743 ảnh full-frame localization |
| Classes / format | 11 class: Articulated truck, Bicycle, Bus, Car, Motorcycle, Non-motorized vehicle, Pedestrian, Pickup truck, Single-unit truck, Work van, Background (classification); localization dùng cùng 11 lớp + "Motorized vehicle" gộp |
| License | CC BY-NC-SA 4.0 (xác nhận trên trang chính thức) |
| Xe máy | Có — class "Motorcycle" riêng biệt, hiếm dataset quốc tế nào trong khảo sát này có nhãn xe máy tường minh cùng lúc với pickup/truck/bus/car |
| Đánh giá | Ứng viên mạnh nhất trong nhóm B: có đủ car, pickup truck (tách riêng khỏi truck thường), single-unit truck, articulated truck, bus, và motorcycle trong cùng 1 dataset, cỡ mẫu rất lớn (786k ảnh), license rõ ràng (chỉ giới hạn phi thương mại + share-alike, hợp mục đích học thuật) — điểm trừ: ảnh chụp từ camera giao thông Bắc Mỹ, tỷ lệ xe máy trong giao thông ở đó rất thấp nên số ảnh motorcycle thực tế trong 648k khả năng chỉ chiếm phần nhỏ (chưa xác minh được số liệu per-class cụ thể trong phiên này) |

Nguồn: [tcd.miovision.com/challenge/dataset.html (WebFetch 2026-07-30)](https://tcd.miovision.com/challenge/dataset.html).

---

### B3. UA-DETRAC

| Mục | Nội dung |
|---|---|
| URL / host | Trang chính thức `detrac-db.rit.albany.edu` — theo WebSearch thì trang này đã đóng từ 24/5/2024, không còn mở được trực tiếp; chỉ còn mirror qua Roboflow Universe (vd `universe.roboflow.com/vehicle-detection-loakn/ua-detrac-10k-sample`) và Kaggle |
| Trích dẫn | L. Wen, D. Du, Z. Cai, Z. Lei, M.-C. Chang, H. Qi, J. Lim, M.-H. Yang, and S. Lyu, "UA-DETRAC: A New Benchmark and Protocol for Multi-Object Detection and Tracking," *Computer Vision and Image Understanding*, vol. 193, 102907, 2020 (bản đầu arXiv:1511.04136, 2015). |
| Size | ~140.000 khung hình (10 giờ video, 24 địa điểm), 8.250 xe gán nhãn tay, 1,21 triệu bounding box |
| Classes / format | Chỉ 4 class: Car, Bus, Van, Others — bbox theo từng khung hình video (không phải ảnh tĩnh riêng lẻ) |
| License | Trang gốc đã đóng nên không xác minh được điều khoản chính thức; mirror trên Roboflow ghi CC BY 4.0 (license của bản mirror, chưa chắc đúng license gốc của tác giả) |
| Xe máy | Không có (gộp vào "Others" nếu có xuất hiện, không tách riêng) |
| Đánh giá | Không hợp cho bài toán phân loại kiểu dáng chi tiết — chỉ 4 lớp rất thô, lại đang trong tình trạng nguồn gốc bị gỡ nên độ tin cậy license/tính toàn vẹn dữ liệu thấp hơn các lựa chọn khác; chỉ nên dùng làm benchmark đối chiếu tracking, không phải nguồn train phân loại kiểu dáng |

Nguồn: [ScienceDirect Wen và cộng sự 2020](https://www.sciencedirect.com/science/article/abs/pii/S1077314220300035); tình trạng site đóng — [WebSearch tổng hợp 2026-07-30]; license mirror Roboflow — [WebSearch snippet 2026-07-30].

---

### B4. Kaggle — TAU Vehicle Type Recognition Competition

| Mục | Nội dung |
|---|---|
| URL / host | [kaggle.com/c/vehicle](https://www.kaggle.com/c/vehicle) — Kaggle competition (Tampere University) |
| Size | Chưa xác định được số ảnh chính xác trong phiên này (trang không hiển thị rõ qua r.jina.ai); nguồn gốc là tập con gán nhãn từ Open Images (bộ gốc >9 triệu ảnh, phần dùng cho competition này nhỏ hơn nhiều, chưa xác minh con số cụ thể) |
| Classes / format | 17 class: Ambulance, Boat, Cart, Limousine, Snowmobile, Truck, Barge, Bus, Caterpillar, Motorcycle, Tank, Van, Bicycle, Car, Helicopter, Segway, Taxi — classification |
| License | Dữ liệu gốc từ Open Images (theo Google thì ảnh Open Images dùng CC BY 2.0, nhưng chưa xác minh trực tiếp license áp dụng riêng cho bản export của competition này); luật lệ competition ghi "không được dùng dữ liệu ngoài" nhưng đó là quy định thi đấu, không phải điều khoản sử dụng ảnh |
| Xe máy | Có — class "Motorcycle" riêng biệt |
| Đánh giá | Có nhãn motorcycle + truck + bus + car + van trong cùng dataset, nhưng danh sách 17 class lệch nhiều về phương tiện không liên quan bãi xe (Boat, Cart, Snowmobile, Tank, Helicopter, Segway...) nên sẽ phải lọc bỏ phần lớn; license chưa rõ ràng vì là dữ liệu competition phái sinh từ Open Images. Giá trị chính của việc xem dataset này: xác nhận thêm là Open Images có nhãn motorcycle, nếu sau này cần tự trích subset khác trực tiếp từ Open Images (chưa khảo sát trực tiếp Open Images gốc trong phiên này) |

Nguồn: [r.jina.ai render 2026-07-30](https://r.jina.ai/https://www.kaggle.com/c/vehicle); danh sách 17 class — [GitHub UserSaiVarma/TAU-Vehicle-Type-Recognition-Competition (WebSearch snippet trích nguyên văn, 2026-07-30)](https://github.com/UserSaiVarma/TAU-Vehicle-Type-Recognition-Competition).

---

## C. Đối chiếu với nguồn Việt Nam đã tìm trước đó + 2 nguồn VN mới (không đủ điều kiện dùng)

### C1. Vehicle Vietnam-CanTho (đã có trong note trước, mục B2)

4 class rõ ràng: Car, Truck, Bus, Motorbike — CC BY 4.0, 1.110–1.746 ảnh, đường phố Cần Thơ ban ngày. Không phân biệt kiểu dáng xe con (chỉ 1 lớp "Car" gộp mọi loại sedan/SUV/hatchback) — đây chính là lý do khảo sát này được làm: cần bổ sung độ chi tiết car-subtype mà B2 không có. Chi tiết đầy đủ: xem `docs/research/2026-07-30-parking-vehicle-plate-datasets.md`, mục B2.

### C2. "Vietnamese vehicle" v3 (đã có trong note trước, mục B1) — vẫn chưa xác minh được 8 class

Thử lại mở trang [universe.roboflow.com/car-classification/vietnamese-vehicle/dataset/3](https://universe.roboflow.com/car-classification/vietnamese-vehicle/dataset/3) qua r.jina.ai lần nữa trong phiên này — vẫn không lấy được danh sách 8 "remapped classes" cụ thể (trang chỉ hiện số liệu tổng: 1.547 ảnh, CC BY 4.0, publish 2/2023; mô tả gốc tìm qua WebSearch xác nhận lại class ban đầu là "car-bus-truck-motorcycle" 4 lớp trước khi remap). Câu hỏi mở #2 của note trước vẫn chưa giải quyết được — cần xem trực tiếp qua giao diện web hoặc tải thử để biết chính xác 8 lớp là gì (có thể là 4 lớp gốc × 2 trạng thái, hoặc đã tách thêm sedan/SUV — không thể khẳng định).

### C3. Kaggle — "Vietnamese Vehicles Dataset" (duongtran1909) — không dùng được cho classification

| Mục | Nội dung |
|---|---|
| URL | [kaggle.com/datasets/duongtran1909/vietnamese-vehicles-dataset](https://www.kaggle.com/datasets/duongtran1909/vietnamese-vehicles-dataset) |
| Size | 98.500 file, 4,09 GB, chia 2 thư mục `daytime-dataset` / `nighttime-dataset`, chụp tại TP.HCM |
| Classes / format | Không có nhãn lớp nào — chỉ có 2 thư mục theo thời điểm chụp (ngày/đêm), không có cấu trúc theo kiểu dáng xe; mô tả dataset để trống |
| License | Không nêu (mục License trên trang trống) |
| Đánh giá | Cỡ ảnh lớn và có bối cảnh VN thật (đáng để ý cho phần đa dạng ánh sáng ngày/đêm), nhưng hoàn toàn không có nhãn phân loại nên không dùng trực tiếp cho classification được — chỉ có giá trị nếu tự gán nhãn lại, mà 98,5k ảnh thì khá tốn công |

Nguồn: [r.jina.ai render 2026-07-30](https://r.jina.ai/https://www.kaggle.com/datasets/duongtran1909/vietnamese-vehicles-dataset/data).

### C4. Kaggle — "Vietnam Automobile Dataset" (qucvinhdng) — không phải dữ liệu ảnh, loại khỏi khảo sát

Kiểm tra thì đây là dữ liệu dạng bảng (tabular) cào từ trang rao vặt xe cũ `bonbanh.com` — các trường là hãng xe, năm sản xuất, tình trạng cũ/mới, giá, địa điểm, số km đã đi. Không phải ảnh, không có nhãn kiểu dáng xe dùng được cho classification bằng ảnh. Loại khỏi khảo sát này, ghi lại để khỏi mất công kiểm tra lại lần sau.

---

## D. Bảng so sánh tổng hợp

| Dataset | Host | Size | Classes (nguyên văn) | Annotation | License (đã kiểm tra) | Có xe máy? |
|---|---|---|---|---|---|---|
| Vehicle Body Style Dataset (A1) | Roboflow | 10.000 | 12 (giống CompCars) | Detection (bbox) | CC BY 4.0 | Không |
| Stanford Cars / Cars196 (A2) | Stanford / TFDS mirror | 16.185 | 196 make/model/year (không có body-type gốc) | Classification + bbox | Mâu thuẫn/chưa rõ (TFDS ghi CC BY 4.0, gốc không mở được) | Không |
| CompCars (A3) | CUHK MMLab | 136.726 (+27.618 part) web + 50.000 surveillance | 12: MPV/SUV/hatchback/sedan/minibus/fastback/estate/pickup/sports/crossover/convertible/hardtop convertible | Classification + bbox + viewpoint | Phi thương mại, nghiên cứu only | Không |
| VMMRdb (A4) | GitHub (faezetta) | 291.752 | 9.170 make/model/year (không có body-type) | Classification | MIT | Không |
| Stanford Car Body Type Data (A5) | Kaggle (derived) | 8.146 | hatchback/sedan/SUV/... (gán nhãn lại phi chính thức từ A2) | Classification (folder) | "Other" — chưa rõ chi tiết | Không |
| VTID2 (A6) | Mendeley (+Kaggle mirror) | 4.356 (Mendeley) / 4.793 (mirror, chênh lệch chưa rõ) | 5: Sedan/Pick-up/SUV/Hatchback/Other | Classification (folder) | CC BY 4.0 | Không |
| BIT-Vehicle (B1) | Trang chính thức BIT — không mở được | 9.850 | 6: Bus/Microbus/Minivan/Sedan/SUV/Truck | Classification + bbox | Chưa xác minh — trang nguồn lỗi DNS | Không |
| MIO-TCD (B2) | Miovision (chính thức) | 786.702 (648.959 classification) | 11: Articulated truck/Bicycle/Bus/Car/Motorcycle/Non-motorized vehicle/Pedestrian/Pickup truck/Single-unit truck/Work van/Background | Classification + localization | CC BY-NC-SA 4.0 | Có (Motorcycle), tỷ lệ thấp (Bắc Mỹ) |
| UA-DETRAC (B3) | Site gốc đóng 5/2024; mirror Roboflow/Kaggle | ~140.000 khung hình, 8.250 xe | 4: Car/Bus/Van/Others (thô, không tách kiểu dáng) | Bbox theo video | Gốc không rõ; mirror ghi CC BY 4.0 | Không (gộp "Others") |
| TAU Vehicle Type Recognition (B4) | Kaggle competition (Open Images) | Chưa xác định | 17: Ambulance/Boat/Cart/Limousine/Snowmobile/Truck/Barge/Bus/Caterpillar/Motorcycle/Tank/Van/Bicycle/Car/Helicopter/Segway/Taxi | Classification | Chưa rõ (phái sinh Open Images) | Có (Motorcycle) |
| Vehicle Vietnam-CanTho (C1, = B2 note trước) | Roboflow | 1.110–1.746 | 4: Car/Truck/Bus/Motorbike (không tách kiểu dáng xe con) | Detection (bbox) | CC BY 4.0 | Có |
| Vietnamese vehicle v3 (C2, = B1 note trước) | Roboflow | 1.547 | 8 remapped classes — vẫn chưa xác minh được danh sách cụ thể | Detection (bbox) | CC BY 4.0 | Không rõ |
| Vietnamese Vehicles Dataset (C3) | Kaggle | 98.500 file | Không có nhãn lớp (chỉ ngày/đêm) | Không có | Không nêu | Không rõ |
| Vietnam Automobile Dataset (C4) | Kaggle | ~4.046 bản ghi | Dữ liệu bảng (hãng/năm/giá), không phải ảnh | N/A — tabular | Không nêu | N/A |

---

## E. Khuyến nghị

Không dataset công khai đơn lẻ nào bao phủ đủ cả 5 lớp mục tiêu (sedan, SUV, pickup, truck, motorbike) trong cùng một bộ nhãn nhất quán. Cần kết hợp theo hướng 2 tầng (car-subtype riêng + coarse-type riêng):

1. **Cho phần kiểu dáng xe con (sedan/SUV/hatchback/MPV):** dùng CompCars (A3) làm nguồn tham chiếu chính cho danh sách 12 kiểu dáng chuẩn (nếu chấp nhận điều khoản phi thương mại và thủ tục xin tải), hoặc VTID2 (A6, CC BY 4.0) nếu cần license dễ dùng hơn và chấp nhận cỡ mẫu nhỏ hơn nhiều (4.356 ảnh, chỉ 4 kiểu dáng + "Other" thay vì 12). Roboflow Vehicle Body Style Dataset (A1) là lựa chọn cân bằng — cùng 12 lớp CompCars nhưng license CC BY 4.0 và có bounding box; đây là dataset nhóm đã chọn (xem mục G).
2. **Cho phần pickup/truck/bus (phân biệt khỏi "car" nói chung):** MIO-TCD (B2) là lựa chọn tốt nhất — 786k ảnh, tách rõ pickup truck / single-unit truck / articulated truck / bus / car, license CC BY-NC-SA 4.0 rõ ràng, và là dataset quốc tế duy nhất trong nhóm B có sẵn nhãn motorcycle dù tỷ lệ thấp. Có thể dùng làm nguồn bổ sung cho pickup/truck/bus mà dataset VN hiện có (Vehicle Vietnam-CanTho) không tách chi tiết.
3. **Cho phần xe máy (motorbike) — khoảng trống lớn nhất:** không dataset Tây phương nào trong khảo sát này có tỷ lệ motorcycle đủ lớn hoặc đa dạng kiểu xe máy VN (xe số, tay ga, wave/dream phổ biến ở VN). Cần dựa vào nguồn Việt Nam: Vehicle Vietnam-CanTho (đã có, class Motorbike riêng, nhưng cỡ nhỏ ~1.100-1.700 ảnh và không tách kiểu xe máy) kết hợp khả năng tự chụp bổ sung ảnh xe máy tại cổng bãi xe (đã nêu ở note trước, mục F/G) — có lẽ là hướng khả thi nhất vì không dataset công khai nào (kể cả MIO-TCD) đủ số lượng/đa dạng xe máy kiểu VN.
4. Không khuyến nghị làm nguồn chính: Stanford Cars/A2 (license mâu thuẫn, không có nhãn kiểu dáng gốc), VMMRdb/A4 (không có nhãn kiểu dáng), UA-DETRAC/B3 (chỉ 4 lớp thô, nguồn gốc đã đóng), TAU/B4 (17 lớp lệch, license không rõ), Vietnamese Vehicles Dataset/C3 và Vietnam Automobile Dataset/C4 (không có nhãn phân loại phù hợp).

---

## F. Gap analysis — lớp mục tiêu không được bao phủ đầy đủ

- **Sedan/SUV/hatchback/MPV (car subtype):** phủ tốt nhất về mặt danh sách nhãn (CompCars 12 lớp, VTID2 5 lớp, Vehicle Body Style Dataset 12 lớp) nhưng toàn bộ nguồn đều là ảnh xe Tây/Trung/Thái — không có ảnh xe con đặc thù thị trường Việt Nam (model phổ biến ở VN như Toyota Vios, Honda City, Kia Morning, Hyundai Accent... khác phân phối model so với CompCars/Stanford Cars vốn thiên về xe Mỹ/Trung/châu Âu). Có rủi ro domain gap khi áp dụng model train trên các dataset này cho xe thực tế tại cổng bãi xe VN.
- **Pickup truck:** chỉ MIO-TCD (B2) tách riêng "Pickup truck" khỏi truck thường rõ ràng trong số dataset đã xem; CompCars/A3 có nhãn "pickup" nhưng là xe con kiểu bán tải cỡ nhỏ (Toyota Hilux, Ford Ranger kiểu quốc tế) — chưa xem ảnh mẫu trực tiếp trong phiên này nên chưa biết có khớp pickup phổ biến ở VN không.
- **Truck (xe tải hạng nặng/trung):** MIO-TCD (single-unit/articulated truck) và BIT-Vehicle (Truck, dù link tải hiện lỗi) là 2 nguồn có nhãn truck tách biệt; không dataset nào phân biệt xe tải nhỏ/trung/nặng theo chuẩn VN (biển số nền vàng cho xe kinh doanh vận tải — đã nêu trong CLAUDE.md dự án, không tìm thấy dataset nào liên hệ trực tiếp loại biển này với kiểu xe).
- **Motorbike/xe máy:** gap lớn nhất, không dataset công khai (Tây phương) nào đủ số lượng và đa dạng. MIO-TCD và TAU đều có nhãn "Motorcycle" nhưng cả hai là dữ liệu Bắc Mỹ/Open Images nơi xe máy là phương tiện thiểu số — hình dạng, góc chụp, mật độ giao thông không đại diện cho xe máy VN (nơi xe máy chiếm đa số). Chỉ Vehicle Vietnam-CanTho (nguồn VN đã có từ note trước) có ảnh xe máy VN thật, nhưng cỡ mẫu nhỏ và không tách theo kiểu xe máy (số/tay ga/PKL).
- Từ mấy gap trên, cần phối hợp ít nhất 2–3 nguồn khác nhau (car-subtype quốc tế cho sedan/SUV/hatchback + MIO-TCD cho pickup/truck/bus + Vehicle Vietnam-CanTho cho motorbike VN), và rất có thể vẫn cần tự chụp bổ sung ảnh xe máy VN theo kiểu dáng (xe số/tay ga phổ biến tại cổng bãi xe) vì không nguồn công khai nào đủ đại diện — áp dụng đúng lưu ý quyền riêng tư đã nêu ở `docs/research/2026-07-30-parking-vehicle-plate-datasets.md`, mục G.

---

## G. Bổ sung 2026-07-30 (sau khi tải thật + xem ảnh mẫu qua EDA — A1 Vehicle Body Style Dataset)

Nhóm chọn tải A1 (Roboflow Vehicle Body Style Dataset) và chạy EDA thật (`src/ml/notebooks/eda-vehicle-body-style.ipynb`, số liệu ở `docs/research/eda_outputs/eda_vehicle_body_style_summary.csv`, hình ở `docs/report/figures/eda_vbs_*.png`). Kết quả xác nhận đúng gap đã nói ở mục F bằng ảnh thật, và có thêm vài điểm:

- Xem ảnh mẫu (`eda_vbs_sample_by_class.png`, 3 ảnh/lớp × 12 lớp) thì thấy domain gap rõ ràng: phần lớn ảnh là bối cảnh Trung Quốc (biển hiệu chữ Hán, biển số xe kiểu TQ xuất hiện ở vài ảnh, showroom/auto-show) — đúng như nghĩ lúc khảo sát nguồn (dataset dựa theo CompCars, thu thập ở Trung Quốc). Không có ảnh nào nhận ra là bối cảnh Việt Nam.
- 3/12 lớp gần như không liên quan đến use-case bãi xe VN: Convertible, Sports, Hardtop Convertible chủ yếu là xe thể thao/mui trần hạng sang (Porsche, Lotus, Aston Martin...) — thực tế bãi giữ xe VN thông thường gần như không gặp mấy loại này. Có thể cân nhắc gộp 3 lớp này thành 1 lớp "Sports/Other" hoặc bỏ khỏi tập train nếu mục tiêu là phân loại xe thực tế tại bãi xe.
- Ảnh chủ yếu là kiểu chụp "đẹp" dealer/auto-show/studio (nền sạch, góc chụp quảng cáo), khác hẳn góc camera giám sát cố định ở cổng bãi xe — thấy rõ qua `box_area_ratio` trung bình khá cao (0,31, phân bố hình chuông quanh 0,25–0,35) so với dataset biển số/bối cảnh bãi xe đã khảo sát trước đó (0,028–0,043). Đây là domain gap thứ hai: không chỉ khác model xe (thị trường TQ vs VN) mà còn khác cả kiểu ảnh (studio/quảng cáo vs surveillance).
- Dataset cân bằng lớp gần như hoàn hảo (tỉ lệ max/min chỉ 1,02×, ~825–840 ảnh/lớp) — điểm cộng, không cần xử lý mất cân bằng lớp khi dùng trực tiếp 12 lớp này.
- Kích thước ảnh cũng bị Roboflow resize cố định về 320×320 khi export — giống vấn đề đã gặp với A2/A3 ở note biển số (ký hiệu của note biển số, khác với A2/A3 của note này), mất đa dạng độ phân giải gốc.
- Độ sáng trung bình (83,4) thấp hơn 3 dataset biển số đã khảo sát (100–111) nhưng phân bố vẫn là một cụm hẹp quanh giá trị trung bình — không có bằng chứng đa dạng ngày/đêm thật, giống tình trạng ở các dataset biển số.

Nói chung dataset này hợp để làm nguồn pretrain/transfer learning cho việc phân biệt hình dạng xe (12 lớp cân bằng, rõ ràng), nhưng nếu dùng thật thì vẫn cần fine-tune trên ảnh xe thực tế tại Việt Nam (chụp ở bãi xe/đường phố VN, model xe phổ biến VN) trước khi triển khai — không nên dùng thẳng model train thuần trên dataset này. Điều này càng củng cố cho việc cần tự chụp bổ sung đã nói ở mục F, không chỉ riêng lớp motorbike mà cả car-subtype.

---
