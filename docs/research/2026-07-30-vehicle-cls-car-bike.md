# Dataset cho phân loại xe 2 lớp: **car vs bike (xe máy)** — VN

**Ngày:** 2026-07-30
**Mode:** 3 (dataset). **Bài toán chốt:** classifier **2 lớp** — `car` (ô tô) vs `bike` (xe máy/motorbike). Khớp bậc phí bãi xe VN (ô tô vs xe máy) và module *Phân loại xe* (Nhật, W5).
**Bổ sung cho:** [[2026-07-28-dataset-inventory-verified]] (inventory đã kiểm), [[2026-07-26-datasets-vietnam]] (khảo sát PART 4).

---

## Kết luận nhanh

**Không có** bộ classification VN sạch nào gán sẵn `car` vs `bike`. `nqa112` (V3) là **bicycle vs motorbike** — không có ô tô, lệch mục tiêu.
→ **Giải pháp: crop-from-detection.** Lấy các bộ *detection* xe VN (đã có bbox từng xe), cắt crop từng box, **remap class-id → {car, bike}**. Được hàng nghìn crop 2 lớp sạch, và khớp đúng luồng chạy thật (detector → crop → classify).

**Bộ dùng (gộp):**

| Ưu tiên | Bộ | Trạng thái | Vai trò |
|---|---|---|---|
| 1 | `vehicle_lmphmthanh` (V1) | ✅ đã tải (2.361 ảnh) | nguồn crop chính, CC BY 4.0 |
| 2 | `duongtran1909` (V2) | ⬇️ **cần tải** (~4GB) | thêm crop **ngày + đêm** HCM, **CC0-1.0** |
| 3 | `nqa112` motorbike/ (V3) | tùy chọn | bù crop xe máy; **bỏ** folder `bike/` (xe đạp) |

---

## Chi tiết nguồn (kiểm thật qua Kaggle API 30/07)

### V1 — `lmphmthanh/vietnam-vehicle-dataset` (mirror Roboflow `vietnamese-vehicle v3`)
- **2.361 ảnh**, YOLO bbox, **nc=4** (12.163 box; id1=4.230, id0=3.960, id2=3.310, id3=663), 640×640.
- Class (thứ tự Roboflow): `car, bus, truck, motorcycle`. **License CC BY 4.0 xác minh** (nhúng trong `data.yaml`).
- Đã tải + kiểm ở inventory 28/07. → crop sẵn dùng ngay.

### V2 — `duongtran1909/vietnamese-vehicles-dataset` ⭐ (bộ mới cần thêm)
- Format: **YOLO detection** (cặp `.jpg` + `.txt`), đa camera giao thông HCM.
- **Có 2 nhánh sáng:** `daytime-dataset/daytime/` **và** `nighttime-dataset/nighttime/` → **ban đêm thật** (hiếm, rất giá trị cho bãi xe).
- **nc=4** (class-id 0,1,2,3). Đo histogram mẫu: **id0 áp đảo = xe máy**; id1/2/3 = 4-bánh (car/bus/truck) — **cần xem crop để chốt tên chính xác từng id**.
- **License CC0-1.0** (xác minh qua Kaggle API) → **sạch nhất**, dùng/publish tự do.
- ~4GB → tải riêng, không gộp git.

### V3 — `nqa112/vietnamese-bike-and-motorbike` (biên, tùy chọn)
- **Classification folder=class.** `bike/` = **xe đạp** (200+ ảnh web tạp), có folder `motorbike/` riêng.
- **Không có lớp ô tô** → không giải được car-vs-bike một mình.
- Dùng được: chỉ lấy `motorbike/` làm crop xe máy bổ sung. **Bỏ `bike/`** (xe đạp = nhiễu cho bài 2 lớp).

---

## Công thức remap class → {car, bike}

Quy ước bãi xe VN: **bike = xe máy**; **car = mọi xe 4 bánh** (car + bus + truck + van).

**V1 (`car, bus, truck, motorcycle`):**
```
motorcycle (id3)      -> bike
car,bus,truck (0,1,2) -> car
```

**V2 (`0,1,2,3`, cần xác nhận tên bằng mắt trên crop):**
```
id0 (motorbike)       -> bike
id1,id2,id3 (4-bánh)  -> car
```
⚠️ **Trước khi train phải mở ~30 crop mỗi id của V2** để chốt id nào là xe máy (dày, box nhỏ) vs 4-bánh. Không đoán mù.

**V3:** chỉ `motorbike/*` -> `bike`.

---

## Cân bằng lớp (rủi ro chính)

Data VN **nghiêng xe máy nặng** (id0 áp đảo). Sau crop → `bike` >> `car`.
Xử lý:
1. Gộp **car+bus+truck** của V1/V2 vào `car` → tăng mẫu car.
2. **Oversample/augment** lớp `car` (flip, color-jitter, crop-scale) khi train.
3. Hoặc **cap** số crop `bike` ~ ngang `car` (undersample) để 1:1.
4. Báo cáo: nêu rõ tỉ lệ car:bike trước/sau cân bằng.

Ban đêm (V2 night) thường ít xe → giữ lại toàn bộ crop đêm cho robustness, đừng cắt.

---

## Kế hoạch build (đề xuất)

1. `kaggle datasets download duongtran1909/vietnamese-vehicles-dataset` (~4GB, ngoài repo).
2. Script `crop_vehicles.py`: đọc từng `img/label`, cắt bbox theo YOLO norm, ghi ra `crops/{car,bike}/` theo remap trên. Chạy cho V1 + V2 (+ V3 motorbike/).
3. Kiểm mắt montage mỗi lớp (như `montage.py` đã có) → xác nhận id V2, loại crop rác (box quá nhỏ < ~24px, cắt lẹm).
4. Split train/val/test **theo camera/ảnh gốc** (không để crop cùng 1 ảnh rơi cả train+test → rò rỉ).
5. Train MobileNetV3/ResNet18 2 lớp (skill `ml-training`).

→ Tôi có thể tải V2 + viết `crop_vehicles.py` ngay nếu bạn muốn.

---

## Còn thiếu → hành động
1. **Chốt tên class-id V2** bằng montage crop (bắt buộc trước train).
2. Nếu muốn thêm car đêm: V2 night là nguồn duy nhất hiện có; cân nhắc tự thu thêm.
3. COCO/MIO-TCD chỉ để **pretrain** nếu car quá ít — domain gap xe máy VN, không dùng đánh giá.

**Feeds into:** Module *Phân loại xe* (Nhật, W5); Chương "Dữ liệu" (W2) — bổ sung nhánh vehicle classification 2 lớp. Bib: `duongtran2022vnvehicles`, `nqa112023bikemotorbike`, `lmphmthanh` (đã có).
