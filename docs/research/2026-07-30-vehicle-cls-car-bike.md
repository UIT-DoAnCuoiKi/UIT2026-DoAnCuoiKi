# Dataset phân loại xe 2 lớp: car vs bike (xe máy) - VN

**Ngày tạo:** 2026-07-30 | **Mode:** 3 (dataset)
**Mục đích:** classifier 2 lớp `car` (ô tô) vs `bike` (xe máy) - khớp bậc phí bãi xe VN và module Phân loại xe (Nhật, W5). Bổ sung cho [[2026-07-28-dataset-inventory-verified]], [[2026-07-26-datasets-vietnam]] (Part 4).

---

## Kết luận

Không có bộ classification VN sạch gán sẵn `car` vs `bike`. `nqa112` (V3) là bicycle vs motorbike - không có ô tô.
-> **Giải pháp: crop-from-detection.** Lấy bộ detection xe VN (đã có bbox), cắt crop từng box, remap class-id -> {car, bike}. Được hàng nghìn crop 2 lớp sạch, khớp luồng chạy thật (detector -> crop -> classify).

| Ưu tiên | Bộ | Trạng thái | Vai trò |
|---|---|---|---|
| 1 | `vehicle_lmphmthanh` (V1) | [dùng] đã tải (2.361 ảnh) | nguồn crop chính, CC BY 4.0 |
| 2 | `duongtran1909` (V2) | cần tải (~4GB) | crop ngày + đêm HCM, CC0 |
| 3 | `nqa112` motorbike/ (V3) | tùy chọn | bù crop xe máy; bỏ folder `bike/` (xe đạp) |

---

## Chi tiết nguồn (kiểm thật qua Kaggle API 30/07)

**V1 - `lmphmthanh/vietnam-vehicle-dataset`** (mirror Roboflow `vietnamese-vehicle v3`)
- 2.361 ảnh, YOLO bbox, nc=4 (12.163 box; id1=4.230, id0=3.960, id2=3.310, id3=663), 640×640.
- Class (thứ tự Roboflow): `car, bus, truck, motorcycle`. License CC BY 4.0 xác minh (trong `data.yaml`). Crop dùng ngay.

**V2 - `duongtran1909/vietnamese-vehicles-dataset`** (cần thêm)
- YOLO detection (`.jpg` + `.txt`), đa camera giao thông HCM.
- 2 nhánh sáng: `daytime-dataset/` và `nighttime-dataset/` -> ban đêm thật (hiếm, giá trị cho bãi xe).
- nc=4 (id 0-3). Histogram mẫu: id0 áp đảo = xe máy; id1/2/3 = 4-bánh - cần xem crop chốt tên từng id.
- License CC0-1.0 (xác minh Kaggle API) -> sạch nhất, dùng/publish tự do. ~4GB -> tải riêng, không gộp git.

**V3 - `nqa112/vietnamese-bike-and-motorbike`** (biên, tùy chọn)
- Classification folder=class. `bike/` = xe đạp (200+ ảnh web tạp); `motorbike/` riêng.
- Không có lớp ô tô -> không giải car-vs-bike một mình. Chỉ lấy `motorbike/` bù crop xe máy; bỏ `bike/`.

---

## Remap class -> {car, bike}

Quy ước: bike = xe máy; car = mọi xe 4 bánh (car + bus + truck + van).

**V1** (`car, bus, truck, motorcycle`): `motorcycle (id3) -> bike`; `car,bus,truck (0,1,2) -> car`.
**V2** (`0,1,2,3`): `id0 (motorbike) -> bike`; `id1,id2,id3 (4-bánh) -> car`.
Lưu ý: trước train phải mở ~30 crop mỗi id của V2 để chốt id nào là xe máy (dày, box nhỏ) vs 4-bánh. Không đoán mù.
**V3:** chỉ `motorbike/*` -> `bike`.

---

## Cân bằng lớp (rủi ro chính)

Data VN nghiêng xe máy nặng (id0 áp đảo). Sau crop -> `bike` >> `car`. Xử lý:
1. Gộp car+bus+truck của V1/V2 vào `car` -> tăng mẫu car.
2. Oversample/augment lớp `car` (flip, color-jitter, crop-scale).
3. Hoặc cap crop `bike` ~ ngang `car` (undersample) để 1:1.
4. Báo cáo tỉ lệ car:bike trước/sau cân bằng.

Ban đêm (V2 night) thường ít xe -> giữ toàn bộ crop đêm cho robustness.

---

## Kế hoạch build

1. `kaggle datasets download duongtran1909/vietnamese-vehicles-dataset` (~4GB, ngoài repo).
2. `crop_vehicles.py`: đọc `img/label`, cắt bbox YOLO norm, ghi `crops/{car,bike}/` theo remap. Chạy V1 + V2 (+ V3 motorbike/).
3. Montage mỗi lớp -> xác nhận id V2, loại crop rác (box < ~24px, cắt lẹm).
4. Split train/val/test theo camera/ảnh gốc (không để crop cùng 1 ảnh rơi cả train+test -> rò rỉ).
5. Train MobileNetV3/ResNet18 2 lớp (skill `ml-training`).

---

## Còn thiếu -> hành động

1. Chốt tên class-id V2 bằng montage crop (bắt buộc trước train).
2. Thêm car đêm: V2 night là nguồn duy nhất; cân nhắc tự thu.
3. COCO/MIO-TCD chỉ pretrain nếu car quá ít - domain gap xe máy VN, không dùng đánh giá.

**Feeds into:** Module Phân loại xe (Nhật W5); Chương Dữ liệu (W2). Bib: `duongtran2022vnvehicles`, `nqa112023bikemotorbike`, `lmphmthanh`.
