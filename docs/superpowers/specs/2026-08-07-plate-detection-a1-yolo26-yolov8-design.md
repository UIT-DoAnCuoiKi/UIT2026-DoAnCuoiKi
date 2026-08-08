# Design — Pipeline phát hiện vùng biển số trên A1 (YOLO26n vs YOLO8n)

**Ngày:** 2026-08-07 · **Giai đoạn:** Tuần 3 (Phát hiện & Màu biển) · **Phụ trách:** Nguyễn Minh Nhật
**Trạng thái:** Design — **reviewed 2026-08-08** (khoa học OK; sửa 2 factual + 4 gap, xem changelog) → sẵn sàng lập implementation plan
**Liên quan:** đề cương `docs/DCDATN_...pdf` (mục tiêu cụ thể 1), EDA `src/ml/notebooks/eda-plate-datasets.ipynb`, khảo sát dataset `docs/research/2026-07-30-parking-vehicle-plate-datasets.md` (mục A1), kiến trúc YOLO `docs/research/2026-07-18-yolo-architecture.md`. Skills: `ml-training`, `alpr-pipeline`.

> **Review changelog (2026-08-08, agent-data-ml-model):** khoa học vững, khả thi. **Sửa factual:** F1 chạy **local, OS-independent** (Win/Mac/Linux) — data đã có local, device auto-detect, package không hardcode path/env (§4/§8/D7); F2 resolution thật W335–4032/H255–3024 px + bug `eda_summary.csv` (§5, R7). **Thêm/siết:** D11+§9.8 imgsz-ablation 960; §6.4 dedup thêm train↔val; §6.3 định nghĩa stratify-key; §6.2 yaml names `['BSD','BSV']` phải verify; §9.1 S=3 = descriptive, KHÔNG paired-test. **Impl:** redo-clean từ design mới (bỏ code cũ 5-commit); chưa bắt đầu.

---

## 1. Bối cảnh & mục tiêu

Đề tài lớn (quản lý bãi xe thông minh) cần mô-đun **nhận diện biển số** = *phát hiện vùng biển* → OCR → màu nền → CSDL vào/ra. Spec này chỉ đặc tả **stage phát hiện vùng biển số** (deliverable Tuần 3 của Nhật), đầu vào cho các stage sau.

**Mục tiêu:** train detector vùng biển trên **A1** (Kaggle `duydieunguyen/licenseplates`), **so sánh YOLO26n vs YOLO8n bằng phương pháp đáng tin cậy**, xuất weights + ONNX + API `PlateDetector`; code viết dạng **package mở rộng được**, kèm bảng số liệu + hình cho báo cáo.

**Đầu ra khớp bài toán lớn:** contract `PlateDetection{bbox, layout(1/2 hàng), conf, crop}`, backend-swap `pt` (PC) / `onnx` (edge).

---

## 2. Phạm vi

**Trong:** package `src/ml/plate_detect/` (prepare · train · eval · export · inference · tests) + notebook/CLI driver mỏng (local, OS-independent) + bảng/hình báo cáo.
**Ngoài (defer):** INT8 quant + benchmark Pi5 (Tuần 7–8) · gộp A2/A3/A4 (nhưng **thiết kế sẵn adapter để thêm sau**) · OBB/deskew training · pretrain CCPD · OCR/màu/CSDL.

---

## 3. Quyết định thiết kế

| # | Quyết định | Chọn | Lý do |
|---|---|---|---|
| D1 | Hình học output | **Axis-aligned bbox** | 2 model native, export/quant tốt, so sánh sạch. Deskew ở stage sau. |
| D2 | Số class | **2 class** `bien_1hang`/`bien_2hang` | Điểm riêng A1; feed logic tách dòng OCR. |
| D3 | Phạm vi data | **Chỉ A1** (adapter mở rộng được) | Đúng đề bài; thêm dataset sau = thêm adapter. |
| D4 | Test split | **Giữ train, `val`→`val`+`test`** stratified seed=42 + **pHash dedup** | A1 không có test; giảm leakage. |
| D5 | Deliverable | **weights + ONNX FP32 + `PlateDetector` + bảng/hình** | Sẵn sàng downstream; INT8 Tuần 7. |
| D6 | Success target | **mAP@0.5 ≥ 0.90** (report kèm mAP@0.5:0.95, soft ≥0.65) | Đề cương không cho ngưỡng detect. *(chờ xác nhận)* |
| D7 | Lưu weights | **git-lfs** `.pt`/`.onnx`; checkpoint **local dir** lúc train (resumable) | Nano nhỏ, repo tự chứa. |
| **D8** | **Kiến trúc code** | **Python package `plate_detect`, config-driven, có adapter/registry/backend abstraction; notebook mỏng import package** | Mở rộng: thêm dataset/model/backend không sửa lõi; logic là code test được, không nằm trong cell notebook. **OS-independent**: path config + device auto-detect → cùng 1 package chạy Win/Mac/Linux, đổi máy không sửa code. |
| **D9** | **Độ tin cậy eval** | **Multi-seed (S≥3) mean±std + bootstrap 95% CI trên test mAP + pHash** | So sánh 2 model phải loại nhiễu train-randomness → kết luận "A>B" mới đứng vững. |
| **D10** | **Pipeline check** | **Synthetic fixtures + smoke test end-to-end + data-contract validation + `--dry-run`** | Bắt lỗi wiring trước khi tốn giờ train GPU; test đảm bảo chất lượng. |
| **D11** | **Input resolution** | **imgsz=640 baseline + ablate 960 (per-model, 1 seed)** | A1 ảnh 335–4032px, plate nhỏ (area 0.043); letterbox 640 co plate ở ảnh lớn → imgsz có thể là đòn bẩy mAP > cả chọn model. Xem §9.8. |

---

## 4. Kiến trúc — 5 stage + test harness bọc ngoài

```
                 ┌──────────────────── plate_detect (package, pip install -e) ────────────────────┐
data/raw/A1  ──▶ │ [1] data.prepare ─▶ [2] train.trainer ─▶ [3] eval.evaluate ─▶ [4] export ─▶ [5] inference │ ──▶ OCR→màu→CSDL
(polygon,2cls)   │      (adapter)          (registry ×2)        (multi-seed+CI)      (parity)    (PlateDetector) │
                 └───────▲──────────────────▲───────────────────▲─────────────────────▲────────────▲───────────┘
                         │                  │                   │                     │            │
                 [0] check harness: pytest (unit) · smoke test (fixtures, 1-epoch end-to-end) · data-contract validate · --dry-run
                 driver: notebooks/train-plate-det.ipynb (local, OS-independent — mỏng) HOẶC plate_detect.cli chạy thẳng
```

**Chạy local, OS-independent** (Windows/Mac/Linux) — package **không hardcode path/môi trường**: path từ config, device auto-detect (`torch.cuda.is_available()` → GPU máy nếu có, else CPU). **Data đã có local**: `data/raw/kaggle_vn_plate_segment` (4578 ảnh). Checkpoint → local dir (resumable). Stage [0] fixtures nhỏ = gate trước khi train thật. Weights git-lfs.

---

## 5. Sự thật về A1 (từ EDA — căn cứ thiết kế)

| Mục | Giá trị |
|---|---|
| Ảnh | 4578 (train 3433 / val 1145, **không có test**) |
| Nhãn | polygon 4 góc normalized `class x1 y1 … x4 y4` |
| Class | 2 — yaml names **`['BSD','BSV']`** (viết tắt → id↔layout **phải verify** §6.2). Imbalance 2.2x: **class 0 BSD = 1641 (minority)**, class 1 BSV = 3559 |
| Độ phân giải | gốc **W 335–4032 / H 255–3024 px**, median ~380 (verified 2026-08-08 vs raw). Không resize on-disk. ⚠️ `eda_summary.csv` ghi sai "600×799" — bug artifact (R7) |
| Ánh sáng | ~11% "tối" (proxy độ sáng, không phải nhãn đêm) |
| Bối cảnh | camera cổng bãi, **timestamp DVR cháy góc** |
| Biển | object nhỏ (box_area_ratio mean ~0.043) |
| License | **"Unknown"** → risk R1 |

---

## 6. Package layout & thiết kế mở rộng (D8)

```
src/ml/plate_detect/
  pyproject.toml               # pip install -e . (local, OS-independent: Win/Mac/Linux)
  plate_detect/
    __init__.py
    config.py                  # dataclass Config (paths, hyperparams) + load/merge yaml — KHÔNG hardcode
    data/
      adapters.py              # DatasetAdapter (Protocol) + A1Adapter (polygon→bbox, 2-class)
      prepare.py               # orchestrate: adapter → split → dedup → validate → processed/
      class_map.py             # verify id↔layout (yaml + visual + aspect-ratio)
      dedup.py                 # pHash near-dup train↔test
      validate.py              # data-contract checks (fail loud)
    train/
      registry.py              # MODEL_REGISTRY = {'yolov8n':'yolov8n.pt','yolo26n':'yolo26n.pt'} — thêm model = 1 dòng
      trainer.py               # wrapper ultralytics, model-agnostic, seed-param
    eval/
      metrics.py               # mAP/per-class + latency (model-only vs e2e) + bootstrap CI
      evaluate.py              # multi-seed aggregate, comparison table, figures
    export/
      to_onnx.py               # export + parity check
    inference/
      postprocess.py           # decode family-aware: v8 NMS vs v26 NMS-free (N,300,6)
      plate_detector.py        # PlateDetector API (backend pt|onnx)
    cli.py                     # entrypoints: prepare|train|eval|export|check (argparse, --dry-run)
  configs/
    a1_det.yaml                # dataset yaml (nc=2, names)
    default.yaml               # hyperparams (imgsz, epochs, batch, augment, seeds)
    split/{train,val,test}.txt # manifests (commit; ảnh gitignored)
  tests/
    fixtures/                  # synthetic mini-dataset (rectangle "plate" + polygon) — few KB, tránh license A1
    test_class_map.py test_prepare_bbox.py test_split.py test_dedup.py
    test_validate.py test_postprocess.py test_plate_detector.py test_pipeline_smoke.py
  notebooks/
    train-plate-det.ipynb      # driver mỏng (local, OS-independent), import plate_detect (adapt từ detect-yolov8.ipynb)
  weights/                     # git-lfs: {yolov8n_a1,yolo26n_a1}_seed{k}.pt + best *.onnx
```
Kết quả log vào **`src/ml/experiments.csv`** (ledger chung sẵn có, schema `date,model,dataset,hyperparams,mAP50,mAP50-95,precision,recall,weights`).

**Ba trục mở rộng (đúng nhu cầu tương lai của đề tài):**
1. **Thêm dataset** (A2/A3/A4 per khảo sát E.1) → viết `A2Adapter(DatasetAdapter)`, không đụng train/eval.
2. **Thêm model** (YOLO khác, hay detector xe) → 1 dòng `registry.py`.
3. **Thêm backend/target** (TensorRT, OpenVINO cho edge) → thêm nhánh backend trong `plate_detector.py`.
Tất cả **config-driven** (`config.py` + yaml) — không hardcode path/hyperparam.

---

## 7. Stage details

### [1] Data prep (`data/prepare.py`, `data/adapters.py`)
**Vào:** `data/raw/kaggle_vn_plate_segment/{images,labels}/{train,val}` (đã có local). **Ra:** `data/processed/a1_det/{images,labels}/{train,val,test}` + `configs/a1_det.yaml` + `configs/split/*.txt`.
- **6.1 A1Adapter — poly→bbox:** `xc=(min+max)/2, w=max−min` (x,y), clamp `[0,1]`, drop degenerate. Polygon gốc giữ ở raw cho deskew sau.
- **6.2 class_map verify (GATE):** A1 `dataset.yaml` names = **`['BSD','BSV']`** (viết tắt, nghĩa KHÔNG hiển nhiên → bắt buộc verify). Giả thuyết: BSD=dài→1hang, BSV=vuông→2hang. **Render ≥8 crop/id xác nhận bằng mắt** long/1-row vs square/2-row + aspect-ratio auto-check. Fail loud nếu mâu thuẫn. Sau confirm cố định `0(BSD):bien_1hang, 1(BSV):bien_2hang`.
- **6.3 split:** giữ `train`, chia `val`→`val`+`test` ~50/50 **stratified theo majority-class của ảnh** (ảnh multi-object dùng class chiếm đa số; giữ tỉ lệ BSD/BSV cân giữa val↔test), seed=42, ghi manifest.
- **6.4 dedup:** pHash **train↔test VÀ train↔val** (A1 = DVR cổng, frame liên tiếp gần trùng; val dùng chọn conf operating point §9.4 nên leak val làm threshold lạc quan), Hamming ≤5 ⇒ loại/log, xuất report (đưa vào chương).
- **6.5 validate:** gọi `data/validate.py` (§10).

### [2] Train (`train/trainer.py`, `train/registry.py`)
Model-agnostic wrapper, nhận `model_key ∈ registry`, `seed`. Hyperparam y hệt 2 model (§8). **Pin `ultralytics==8.4.37`** (đã xác nhận có YOLO26; notebook cũ pin 8.3.0 **không có YOLO26** → bump). Checkpoint→local dir/epoch, resumable. Loop S≥3 seeds/model (D9).

### [3] Eval (`eval/evaluate.py`, `eval/metrics.py`)
Trên **A1 test**. Xem §9 (reliable). Append `experiments.csv`, figures→`docs/report/figures/`.

### [4] Export (`export/to_onnx.py`)
best.pt (seed tốt nhất) → ONNX FP32 imgsz 640, **parity check** onnxruntime vs torch (Δ mAP < 1e-3) mới nhận. INT8 defer Tuần 7.

### [5] PlateDetector API (`inference/plate_detector.py`, `inference/postprocess.py`)
```python
@dataclass
class PlateDetection:
    bbox_xyxy: tuple[int,int,int,int]; cls_id: int; cls_name: str; conf: float
    crop: np.ndarray          # axis-aligned + padding, CHƯA deskew
class PlateDetector:
    def __init__(self, weights, backend='pt'|'onnx', conf=..., iou=...): ...
    def detect(self, image) -> list[PlateDetection]: ...
```
Postprocess **family-aware:** v8 cần NMS; v26 NMS-free `(N,300,6)`. Xử no-plate (rỗng)/multi-plate (sort conf)/clamp bbox. `crop` không deskew (D1 — thuộc `alpr-pipeline`).

---

## 8. Chạy local (OS-independent) — notebook hoặc CLI

Package `plate_detect` = pure Python, chạy giống nhau Windows/Mac/Linux. Hai cách chạy, cùng gọi 1 package (logic test được, không nằm trong cell):
- **Notebook** `train-plate-det.ipynb` **mỏng** = chỉ điều phối (adapt từ `detect-yolov8.ipynb`).
- **CLI** `plate_detect.cli` chạy thẳng terminal (script/CI).

**Các bước (giống mọi OS):**
1. `pip install -e .` (cùng `pyproject`, pin `ultralytics==8.4.37`); venv/conda tùy máy.
2. Device **auto-detect** (`torch.cuda.is_available()` → GPU máy nếu có, else CPU). *Train đầy đủ multi-seed nên có GPU local; CPU hợp smoke/dev.*
3. Data đã có local `data/raw/kaggle_vn_plate_segment`.
4. `prepare` → `train`(loop seeds) → `eval` → `export`. Checkpoint/epoch → **local dir**, resumable; weights → git-lfs.

*Khác notebook cũ (`detect-yolov8.ipynb`):* 2-class thay 1-class, pin 8.4.37 (có YOLO26), logic ở package không ở cell.

---

## 9. Đánh giá đáng tin cậy (D9)

**Vấn đề:** so 2 model bằng 1 lần train mỗi bên → chênh mAP có thể là nhiễu seed, không phải model tốt hơn thật. Giải pháp nhiều lớp:

1. **Multi-seed:** train mỗi model **S≥3 seed**; báo cáo **mAP@0.5:0.95 mean ± std**. Ở S=3 → **descriptive only**: kết luận "A>B" chỉ khi khoảng ±std tách nhau rõ. **KHÔNG** claim significance/paired-test ở n=3 (power ~0). Muốn inferential (paired Wilcoxon qua seed) → cần **S≥5** (flag tốn GPU, §9.7).
2. **Bootstrap 95% CI:** resample ảnh test (B≈1000 lần), tính lại mAP → CI phản ánh độ ổn định trên test hữu hạn.
3. **Leakage honesty:** pHash dedup train↔test (§6.4), báo cáo số cặp trùng; coi test là "held-out xấp xỉ".
4. **Cross-check:** per-class AP (imbalance), confusion (1h/2h/bg), PR curve; chọn **conf operating point qua PR trên val** (ưu tiên recall cổng).
5. **Latency tách 2 mức** (đúng đề cương): (a) model-only, (b) end-to-end incl. postprocess/NMS — nơi YOLO26 NMS-free thắng. Warmup + **median**, batch=1, **ghi rõ hardware** (PC dev — CPU/GPU model; Pi5 để Tuần 7–8).
6. **Primary hardware-độc-lập:** params(M)/FLOPs(G)/size(MB) — so sánh không phụ thuộc máy.
7. *(Optional stretch)* stratified **k-fold (k=5)** trên train+val nếu cần chắc hơn — flag tốn GPU.
8. **imgsz ablation (D11):** mỗi model chạy thêm **imgsz=960** (1 seed) so 640 baseline. Plate nhỏ + ảnh tới 4032px → imgsz có thể là đòn bẩy mAP lớn hơn cả chọn model. Báo cáo mAP + latency@imgsz (latency ~scale theo (960/640)²≈2.25×). Nếu 960 thắng rõ → cân nhắc làm imgsz mặc định cho full multi-seed.

**Bảng so sánh:** `model · imgsz · seed(mean±std) mAP@0.5 · mAP@0.5:0.95[CI] · P · R · params · FLOPs · size · lat_model · lat_e2e · FPS`.
**Không** dùng ngưỡng magic ">0.999=leakage" (plate detect dễ, mAP@50 ~0.98 có thể thật) — dùng mAP@0.5:0.95 + pHash + qualitative.
**Qualitative:** grid mẫu + ảnh tối + **check false-positive vùng timestamp DVR**.

**Chi phí:** nano rẻ; 3 seed ×2 model ×~100 epoch trên T4 khả thi. Ngân sách hẹp → tối thiểu S=3.

---

## 10. Pipeline check & test (D10)

| Loại | Nội dung |
|---|---|
| **Fixtures** | `tests/fixtures/` — **synthetic** (vẽ hình chữ nhật "biển" + polygon label), ~20 ảnh vài KB. Tránh commit ảnh A1 (license R1). |
| **Smoke test** `test_pipeline_smoke.py` | Chạy full: prepare→train(**1 epoch, tiny**)→eval→export→`PlateDetector.detect` trên fixtures. Assert wiring + shape + non-crash. CPU < vài phút. **Gate trước khi train GPU thật.** |
| **Unit** | poly→bbox (polygon biết→bbox kỳ vọng) · split determinism+stratify count · dedup · class_map verify · postprocess (v8 NMS vs v26 decode) · `PlateDetection` schema · onnx≈pt parity (tiny). |
| **Data-contract** `data/validate.py` (CLI `check`) | Trên processed: mọi ảnh có label · class id ⊂{0,1} · bbox∈[0,1] · không orphan label · split disjoint · log counts. Fail loud. |
| **Dry-run** | Mỗi CLI stage `--dry-run`: validate config+path, không compute nặng. |
| **Chạy khi nào** | `pytest` + smoke + `check` **trước mỗi commit** và **trước khi launch train GPU** (verification-before-completion). |

---

## 11. Error handling
prepare: assert label · clamp bbox · fail-loud class-map · drop degenerate · validate contract. train: seed+deterministic · checkpoint/epoch · resume · version pre-flight. eval: guard test rỗng · per-class AP · warmup+median. export: parity gate. API: empty/multi/clamp · family-aware postprocess.

## 12. Reproducibility
seed list cố định · manifest + `a1_det.yaml` + `default.yaml` commit · `ultralytics==8.4.37` pin (pyproject) · weights git-lfs · `experiments.csv` 1 dòng/run/seed · `pip install -e` cùng package chạy local mọi OS (Win/Mac/Linux), device auto-detect.

## 13. Risks & open items
- **R1 License A1 "Unknown":** dùng nghiên cứu OK, **liên hệ tác giả trước khi công bố/nộp** (action item). Fixtures synthetic né commit ảnh A1.
- **R2 Leakage dư:** pHash train↔test **+ train↔val** (§6.4) giảm, không loại 100% (thiếu group-id video). Báo cáo minh bạch.
- **R3 Latency PC≠Pi5:** số Tuần 3 trên máy dev indicative; edge thật Tuần 7–8.
- **R4 Imbalance 2.2x:** minority = **class 0 BSD (1-row)**; theo dõi per-class AP class 0; kém → oversample/loss-weight.
- **R5 Compute multi-seed:** S=3 tối thiểu (descriptive); S≥5 nếu cần significance; +imgsz960 ablation ×2 model. Cần **GPU local** cho wall-clock hợp lý; k-fold optional.
- **R6 imgsz vs resolution variance:** ảnh 335–4032px, letterbox 640 co plate nhỏ → ablate 960 (D11/§9.8) lượng hóa.
- **R7 EDA artifact bug:** `docs/research/eda_outputs/eda_summary.csv` cột resolution sai (600×799 vs thực 4032×3024) — sửa artifact + re-run notebook trước khi trích số vào báo cáo.
- **Open (chờ xác nhận):** D6 ngưỡng success.

## 14. Deliverables (map chương Tuần 3)
- [ ] Package `plate_detect` (`pip install -e`) + CLI (`prepare|train|eval|export|check`)
- [ ] class-map verified (yaml+visual) + split manifests + pHash report
- [ ] 2 model × S≥3 seed trained, weights git-lfs
- [ ] Bảng so sánh (mean±std + CI + params/FLOPs/size/latency×2/FPS + imgsz 640 vs 960)
- [ ] mAP@0.5 ≥ 0.90 (D6) + mAP@0.5:0.95 report
- [ ] ONNX FP32 parity-checked + `PlateDetector` (pt|onnx)
- [ ] Test suite (unit + smoke + data-contract) pass; notebook/CLI driver mỏng chạy local (OS-independent)
- [ ] Figures (qualitative + low-light + timestamp FP) → báo cáo · `experiments.csv` cập nhật
