# Kiến trúc YOLO: Từ Grid-Cell Regression đến YOLO26 (Literature Review chuyên sâu)

Mode 1 (literature review học thuật) cho chương Tổng quan của đồ án. Trọng tâm: cơ chế của dòng
YOLO liên quan đến detector xe+biển số của project (YOLOv8/YOLO26 qua Ultralytics, `src/ml/`),
cùng lý do single-stage vs two-stage cho deploy edge trên Raspberry Pi 5.

---

## 1. YOLO gốc (Redmon và cộng sự, 2016) — hợp nhất detection thành một phép regression

**Trích dẫn:** J. Redmon, S. Divvala, R. Girshick, and A. Farhadi, "You Only Look Once: Unified,
Real-Time Object Detection," in *Proc. IEEE Conf. Computer Vision and Pattern Recognition
(CVPR)*, 2016, pp. 779–788. arXiv:1506.02640.
[arXiv abstract](https://arxiv.org/abs/1506.02640) | [arXiv v1](https://arxiv.org/abs/1506.02640v1)

**Tóm tắt:** YOLOv1 định hình lại object detection thành một bài toán regression duy nhất: ảnh
đầu vào chia thành lưới S×S (S=7 trong paper), mỗi ô lưới dự đoán B bounding box (B=2), mỗi box
gồm 4 tọa độ cộng một điểm confidence objectness, và C xác suất class (C=20 cho PASCAL VOC) — một
lần forward pass qua một CNN duy nhất cho ra toàn bộ detection, khác với các pipeline trước đó
(vd họ R-CNN) phải chạy classifier lặp lại trên các region proposal. Tensor output của network là
S×S×(B*5+C). Confidence được định nghĩa là `Pr(Object) * IOU(pred, truth)`, và lúc test,
confidence riêng cho từng class của mỗi box là tích của box confidence và xác suất class có điều
kiện `Pr(Class_i|Object)`. Vì toàn bộ pipeline là một network train end-to-end trực tiếp trên
detection performance, YOLOv1 chạy ở 45 FPS (bản base) đến 155 FPS (Fast YOLO), mAP gần gấp đôi
các detector real-time khác cùng thời, nhưng mắc nhiều lỗi localization hơn hệ two-stage và gặp
khó với vật thể nhỏ/vật thể theo nhóm vì mỗi ô lưới chỉ dự đoán box cho một class và số lượng box
cố định, nhỏ. [Nguồn](https://arxiv.org/abs/1506.02640v1)

**Cấu trúc loss function:** training objective của paper là một sum-of-squared-error loss nhiều
phần với weight riêng cho localization error (`λ_coord=5`), no-object confidence error
(`λ_noobj=0.5`, giảm trọng số vì đa số ô lưới không chứa vật thể), objectness confidence error
cho các ô có chứa vật thể, và classification error — tất cả chỉ tính cho predictor box "chịu
trách nhiệm" (box có IOU cao nhất với ground truth trong ô đó). Điều này thiết lập ba họ loss
(box/localization, objectness/confidence, classification) tồn tại xuyên suốt về mặt khái niệm
qua cả dòng YOLO, dù các loss term cụ thể có thay đổi (xem YOLOv8 bên dưới).
[Nguồn](https://arxiv.org/abs/1506.02640v1)

**Anchor-free vs anchor-based:** YOLOv1 là anchor-free (mỗi ô trực tiếp regress tọa độ box dưới
dạng offset); anchor box được đưa vào sau ở YOLOv2/v3 (prior từ k-means) để cải thiện recall trên
các tỷ lệ khung hình đa dạng, rồi lại bị bỏ ở YOLOv8 (anchor-free, xem §3) — tức là lĩnh vực này
đi từ anchor-free → anchor-based → anchor-free, và detector của mình (YOLOv8) nằm ở phía
anchor-free. [Nguồn: survey Terven & Cordova-Esparza, arXiv:2304.00501]

![YOLOv1 grid-based output prediction format](https://arxiv.org/html/2304.00501v5/extracted/5158657/figures/yolo_output_format.png)
*Hình: định dạng output của YOLO gốc — lưới S×S, mỗi ô cho box + objectness + xác suất class trong một lần forward pass. Nguồn: [Terven & Cordova-Esparza, 2023, arXiv:2304.00501, Fig. 4](https://arxiv.org/abs/2304.00501), minh họa [Redmon và cộng sự, 2016](https://arxiv.org/abs/1506.02640).*

**Liên quan đến hệ thống mình:** Đây là tổ tiên về mặt khái niệm của YOLOv8/YOLO26, dùng cho cả
giai đoạn detect xe và detect biển số trong pipeline ALPR (`src/ml/`, theo hợp đồng của skill
`alpr-pipeline`). Hữu ích cho chương Tổng quan làm câu chuyện gốc "vì sao single-shot detection"
trước khi giải thích lý do chọn bản derivative hiện đại.

```bibtex
@inproceedings{redmon2016yolo,
  author    = {Redmon, Joseph and Divvala, Santosh and Girshick, Ross and Farhadi, Ali},
  title     = {You Only Look Once: Unified, Real-Time Object Detection},
  booktitle = {Proceedings of the IEEE Conference on Computer Vision and Pattern Recognition (CVPR)},
  year      = {2016},
  pages     = {779--788},
  eprint    = {1506.02640},
  archivePrefix = {arXiv}
}
```

---

## 2. Diễn tiến YOLOv3/v4/v5 — vì sao kiến trúc thay đổi

**Trích dẫn (survey bao quát giai đoạn này):** J. Terven and D. Cordova-Esparza, "A Comprehensive
Review of YOLO Architectures in Computer Vision: From YOLOv1 to YOLOv8 and YOLO-NAS," *Machine
Learning and Knowledge Extraction*, 2023. arXiv:2304.00501.
[arXiv abstract](https://arxiv.org/abs/2304.00501) | [HTML full text](https://arxiv.org/html/2304.00501v5)

**Tóm tắt:** Survey này (36 trang, 21 hình) trình bày motivation kiến trúc qua các phiên bản,
dùng ở đây làm nguồn tổng hợp thứ cấp, đối chiếu chéo với docs chính thức của Ultralytics.

- **YOLOv3 (Redmon & Farhadi, 2018):** đưa vào backbone **Darknet-53** 53 tầng có residual
  connection (thay max-pooling bằng strided convolution), cho accuracy top-1/top-5 ngang
  ResNet-152 nhưng tốc độ nhanh gấp khoảng 2 lần. Để khắc phục điểm yếu của YOLOv1/v2 với vật thể
  nhỏ, YOLOv3 thêm **multi-scale prediction** ở ba độ phân giải feature map (13×13, 26×26, 52×52
  cho input 416×416) dùng upsampling + concatenation qua các stage backbone — một thiết kế kiểu
  FPN sơ khai — với 3 anchor prior mỗi scale (9 tổng cộng, từ k-means clustering trên tập train).
  [Nguồn](https://arxiv.org/html/2304.00501v5)
- **YOLOv4 (Bochkovskiy, Wang, Liao, 2020):** backbone chuyển sang **CSPDarknet53** (Cross-Stage
  Partial connection giảm tính toán gradient dư thừa mà vẫn giữ accuracy) với activation Mish;
  neck thêm **SPP** (spatial pyramid pooling, mở rộng receptive field gần như miễn phí) cộng
  **PANet** sửa đổi (concatenation thay vì phép cộng của paper gốc) để fuse feature multi-scale
  bottom-up + top-down. YOLOv4 cũng chính thức hóa phương pháp "Bag of Freebies/Bag of
  Specials" — Mosaic augmentation, DropBlock, CIoU loss, label smoothing (miễn phí — chỉ tốn lúc
  training) vs. Mish, CSP connection, SAM (tăng nhẹ chi phí inference đổi lấy accuracy) — như
  một cách hệ thống để đánh đổi tốc độ vs cải thiện accuracy. [Nguồn](https://arxiv.org/html/2304.00501v5)
- **YOLOv5 (Ultralytics/Jocher, 2020):** viết lại bằng PyTorch (thay vì C của Darknet), giữ
  backbone kiểu CSPDarknet53 với tầng stem Focus/strided-conv để giảm compute, thay SPP bằng
  module **SPPF** nhanh hơn, dùng neck **CSP-PAN** sửa đổi, và thêm **AutoAnchor** để tự động
  re-cluster anchor box theo dataset tùy biến. Tại thời điểm này vẫn anchor-based và vẫn có head
  detection gộp chung (coupled). Ship dưới dạng năm biến thể scale (n/s/m/l/x) khác nhau về
  width/depth network — cùng convention scale width/depth mà YOLOv8 (và các model của project
  này) kế thừa. [Nguồn](https://arxiv.org/html/2304.00501v5); backbone/neck cũng đối chiếu chéo
  với [Ultralytics YOLOv5 docs](https://docs.ultralytics.com/models/yolov5/) và
  [YOLOv5 architecture tutorial](https://docs.ultralytics.com/yolov5/tutorials/architecture-description/).

![Timeline of YOLO versions](https://arxiv.org/html/2304.00501v5/x3.png)
*Hình: timeline các phiên bản YOLO tới mốc cutoff 2023 của survey (v9–v11 và YOLO26 tiếp nối 2024–2026, xem §10). Nguồn: [Terven & Cordova-Esparza, 2023, arXiv:2304.00501, Fig. 1](https://arxiv.org/abs/2304.00501).*

**Hiệu ứng tổng thể qua v3→v5:** mỗi thế hệ đánh đổi độ phức tạp backbone/neck ngày càng tăng
(residual → CSP connection, single-scale → fusion FPN/PANet multi-scale) để lấy recall vật thể
nhỏ tốt hơn và training hiệu quả hơn, trong khi vẫn giữ nguyên thiết kế head cốt lõi "grid + anchor
box + objectness" cho đến khi YOLOv8 phá vỡ nó. [Nguồn: arXiv:2304.00501]

**Liên quan đến hệ thống mình:** Giải thích *vì sao* backbone/neck của YOLOv8 có hình dạng hiện
tại — chúng là hậu duệ trực tiếp của dòng CSP+PAN, không phải thiết kế từ đầu. Hữu ích làm bối
cảnh dòng dõi ngắn gọn trong Tổng quan trước phần đào sâu YOLOv8.

```bibtex
@article{terven2023comprehensive,
  author  = {Terven, Juan and Cordova-Esparza, Diana},
  title   = {A Comprehensive Review of YOLO Architectures in Computer Vision: From YOLOv1 to YOLOv8 and YOLO-NAS},
  journal = {Machine Learning and Knowledge Extraction},
  year    = {2023},
  eprint  = {2304.00501},
  archivePrefix = {arXiv}
}
```

---

## 3. YOLOv8 (Ultralytics) — phiên bản mà code training của mình phụ thuộc vào

**Trích dẫn:** G. Jocher, A. Chaurasia, and J. Qiu, *Ultralytics YOLOv8* (software), version
8.0.0, 2023. [GitHub](https://github.com/ultralytics/ultralytics) |
[Official model docs](https://docs.ultralytics.com/models/yolov8/) |
[Architecture guide](https://docs.ultralytics.com/guides/yolo-architecture/). Ultralytics **chưa**
công bố paper peer-review chính thức cho YOLOv8 — repo GitHub + trang docs là nguồn chuẩn có thể
trích dẫn; các claim kiến trúc dưới đây được đối chiếu chéo giữa trang guide chính thức
`yolo-architecture` và survey Terven & Cordova-Esparza (trích dẫn ở §2), vốn mô tả độc lập cùng
các thành phần này. [Nguồn](https://docs.ultralytics.com/models/yolov8/)

**Tóm tắt cơ chế (backbone → neck → head → loss → label assignment):**

- **Backbone (biến thể CSPDarknet):** trích xuất feature multi-scale ở stride 8/16/32
  (feature map P3, P4, P5), xây từ các block **C2f** xếp chồng ("CSP Bottleneck with 2
  convolutions, faster") và một block **SPPF** cuối. C2f thay thế module **C3** của YOLOv5: thay
  vì chỉ route output bottleneck cuối vào conv fusion, C2f concatenate *tất cả* `n+2` tensor
  feature trung gian dọc theo path split-and-bottleneck trước conv 1×1 cuối cùng — cho gradient
  flow và feature reuse phong phú hơn mà không tăng đáng kể compute, đổi lại activation memory
  cao hơn một chút so với C3. [Nguồn](https://docs.ultralytics.com/guides/yolo-architecture/)
- **Neck (PAN-FPN):** fuse feature backbone P3/P4/P5 theo cả top-down và bottom-up (Path
  Aggregation Network trên nền Feature Pyramid), cùng vai trò topology như PANet/CSP-PAN của
  YOLOv4/v5 nhưng xây lại bằng block C2f thay vì C3. [Nguồn](https://docs.ultralytics.com/guides/yolo-architecture/)
- **Head anchor-free, decoupled:** YOLOv8 bỏ hẳn anchor box — là detector "anchor-free bản
  chất", loại bỏ nhu cầu tinh chỉnh tay anchor prior theo từng dataset (liên quan vì hai class
  vật thể của mình, xe và biển số, có phân bố tỷ lệ khung hình rất khác nhau). Head detection
  **decoupled**: hai nhánh song song mỗi pyramid level, một dự đoán box regression (`4 * reg_max`
  channel, `reg_max=16` mặc định) và một dự đoán điểm số theo class, thay vì một nhánh chung dự
  đoán objectness+class+box cùng lúc như v1–v5. Decoupling giảm nhiễu gradient giữa mục tiêu
  classification và localization. [Nguồn](https://docs.ultralytics.com/guides/yolo-architecture/) và
  [Nguồn](https://arxiv.org/html/2304.00501v5)
- **Task-Aligned Assigner (TAL) cho label assignment:** việc gán positive/negative sample lúc
  training của YOLOv8 dựa trên **Task Alignment Learning của TOOD** (Feng và cộng sự, ICCV 2021),
  không phải rule ngưỡng IoU thiết kế thủ công. `TaskAlignedAssigner` của Ultralytics
  (`ultralytics/utils/tal.py`) chấm điểm mỗi anchor point bằng metric task-alignment
  `t = s^alpha * u^beta` kết hợp điểm classification `s` và IoU `u` giữa box dự đoán và ground
  truth, với mặc định `alpha=0.5`, `beta=6.0`, chọn **top-k** (mặc định `topk=10`) anchor có điểm
  cao nhất mỗi ground-truth object làm positive — thiết kế rõ ràng để giảm sự lệch pha
  classification/localization từng gây khó chịu cho cách gán coupled, dựa ngưỡng IoU trước đây.
  [Nguồn: paper TOOD](https://arxiv.org/abs/2108.07755) |
  [Nguồn: Ultralytics loss.py](https://github.com/ultralytics/ultralytics/blob/main/ultralytics/utils/loss.py) |
  [Nguồn: Ultralytics loss API docs](https://docs.ultralytics.com/reference/utils/loss/).
  **Chú thích độ chính xác (verify lại 2026-07-21):** con số `alpha=0.5`/`topk=10` là giá trị
  `v8DetectionLoss` *truyền vào* khi khởi tạo `TaskAlignedAssigner` trong `loss.py`
  (`TaskAlignedAssigner(topk=tal_topk, num_classes=self.nc, alpha=0.5, beta=6.0, ...)`, với
  `tal_topk=10` mặc định) — chúng **ghi đè** default trong signature của class `tal.py` hiện tại
  (`topk=13, alpha=1.0`). Khi debug đừng lấy nhầm default của signature; giá trị *thực tế lúc train*
  YOLOv8 là 0.5/10/6.0 như trên. `beta=6.0` trùng ở cả hai nơi.
- **Cấu thành loss:** tổng loss = box loss (**CIoU** — Complete IoU, phạt cả khoảng cách tâm và
  lệch tỷ lệ khung hình ngoài overlap) + **DFL** (Distribution Focal Loss, regress mỗi cạnh box
  dưới dạng phân phối xác suất rời rạc trên `reg_max=16` bin qua softmax rồi lấy expectation, thay
  vì một scalar đơn — cải thiện localization biên vật thể nhỏ/mơ hồ) + **BCE** (binary
  cross-entropy) cho classification, chỉ áp dụng trên các anchor positive được TAL chọn.
  [Nguồn](https://docs.ultralytics.com/guides/yolo-architecture/)
  và [Nguồn](https://arxiv.org/html/2304.00501v5)

### 3.1 Đường đi forward pass cụ thể: từ pixel đến bounding box (worked example, YOLOv8n, input 640)

Phần này giải thích *cơ chế* một lần inference — mắt xích các mục §1–§3 mô tả rời rạc — bằng số
liệu cụ thể của YOLOv8n để chương Tổng quan có thể trình bày YOLO "chạy như thế nào", không chỉ
"gồm những gì". Các con số dưới đây đối chiếu với
[Ultralytics YOLO architecture guide](https://docs.ultralytics.com/guides/yolo-architecture/).

1. **Input → backbone (trích feature đa tỷ lệ).** Ảnh RGB 640×640×3 đi qua backbone kiểu
   CSPDarknet. Backbone hạ sample dần và xuất ba feature map ở **stride 8/16/32** — tức P3, P4, P5
   với lưới **80×80, 40×40, 20×20** cho input 640. Stride nhỏ (P3, 80×80) giữ chi tiết không gian
   mịn → bắt vật thể nhỏ (biển số); stride lớn (P5, 20×20) có receptive field rộng → bắt vật thể
   lớn (thân xe). Mỗi lần đi qua block **C2f** (`cv1` split input làm 2 nhánh → `n` Bottleneck nối
   tiếp trên một nhánh → concat cả `n+2` tensor trung gian → `cv2 = Conv((2+n)*c, c2, 1)` fuse) và
   block cuối **SPPF** (`MaxPool2d(k=5, s=1, p=2)` áp 3 lần nối tiếp, concat input + 3 output pool
   rồi conv 1×1) để mở rộng receptive field gần như miễn phí.
   [Nguồn](https://docs.ultralytics.com/guides/yolo-architecture/)
2. **Neck (fuse P3/P4/P5).** PAN-FPN trộn feature theo top-down (ngữ nghĩa từ P5 xuống) rồi
   bottom-up (định vị từ P3 lên), cho mỗi level vừa "biết vật thể là gì" vừa "biết nó ở đâu" trước
   khi vào head. [Nguồn](https://docs.ultralytics.com/guides/yolo-architecture/)
3. **Anchor-free grid → tập "anchor point".** YOLOv8 bỏ anchor box: mỗi ô lưới đóng góp **đúng một
   anchor point** đặt ở tâm ô, tọa độ pixel = `(cx+0.5, cy+0.5) * stride`. Cộng ba level:
   `80×80 + 40×40 + 20×20 = 6400 + 1600 + 400 =` **8400 anchor point / dự đoán ứng viên** cho một
   ảnh 640. Đây là "grid S×S" của YOLOv1 (§1) tổng quát hóa lên đa tỷ lệ và bỏ ràng buộc "một ô
   một class".
4. **Head decoupled xuất channel thô.** Mỗi anchor point cho `nc + 4*reg_max` giá trị (`nc` = số
   class; với project là 2: xe, biển số), tách hai nhánh song song — **nhánh box** `4*reg_max`
   channel (mã hóa 4 khoảng cách cạnh) và **nhánh class** `nc` logit. Khác v1–v5: **không có nhánh
   objectness riêng** — điểm class (sau sigmoid) chính là confidence.
   [Nguồn](https://docs.ultralytics.com/guides/yolo-architecture/)
5. **DFL decode box (distribution → tọa độ).** Nhánh box không regress thẳng 4 số. Module **DFL**
   reshape `4*reg_max` → `(4, reg_max=16)`, softmax trên 16 bin mỗi cạnh, rồi lấy **kỳ vọng** (chỉ
   số bin nhân xác suất, cộng lại) → 4 khoảng cách `(left, top, right, bottom)` tính từ anchor
   point (dạng *ltrb distance-to-edge*). Nhân stride của level → pixel; đổi `ltrb → (x1,y1,x2,y2)`.
   Regress cạnh dưới dạng phân phối rời rạc (thay scalar) cho biên mượt, ổn định hơn ở vật thể
   nhỏ/mờ. [Nguồn](https://docs.ultralytics.com/guides/yolo-architecture/)
6. **Lọc + NMS (chỉ YOLOv8).** Sau bước 5 có tối đa 8400 box thô, phần lớn trùng lặp. Pipeline
   drop box dưới ngưỡng confidence, rồi **Non-Maximum Suppression**: sort theo điểm giảm dần, giữ
   box điểm cao nhất, loại mọi box còn lại có `IoU > iou_thres` (mặc định 0.7) với nó, lặp đến hết
   — kết quả là danh sách detection cuối. NMS là **op tuần tự, dữ liệu-phụ thuộc**, nằm *ngoài*
   graph tensor thuần → thêm latency và làm rối export/quantize ONNX (lý do §4/§9 coi việc YOLO26
   bỏ NMS là lợi thế edge).

**YOLO26 rút gọn bước 4–6:** head **one-to-one** mặc định xuất trực tiếp `(N, 300, 6)` — tối đa 300
detection/ảnh, mỗi dòng `(x1,y1,x2,y2,score,class)` — *không* qua NMS (dual-head: train bằng head
one-to-many như thường, inference bằng head one-to-one). Bỏ DFL nghĩa là nhánh box regress thẳng 4
khoảng cách với *khoảng không ràng buộc*, bỏ luôn softmax-16-bin ở bước 5 → graph gọn hơn cho INT8.
[Nguồn](https://docs.ultralytics.com/models/yolo26/)

**Liên quan hệ thống mình:** đây là mô tả cơ chế trực tiếp trả lời "YOLO hoạt động ra sao" trong
Tổng quan, và là bản đồ để debug config training (`reg_max`, `nc`, `conf`, `iou` NMS) trong
`src/ml/`. Cascade ALPR của mình chạy đúng pipeline này hai lần: pass 1 detect xe trên khung đầy
đủ, crop ROI xe, pass 2 detect biển số trên crop (input phân giải tương đối cao hơn → dễ cho head
P3/vật thể nhỏ, xem §6).

![So sánh YOLO26 vs các phiên bản YOLO trước: mAP vs latency CPU/GPU](https://cdn.jsdelivr.net/gh/ultralytics/assets@main/docs/Ultralytics-YOLO26-Benchmark.jpg)
*Hình: YOLO26 vs YOLO11 / YOLOv10 / YOLOv8 — mAP50-95 (COCO) so với latency CPU ONNX ở mọi scale. YOLO26n/s dẫn đầu trade-off accuracy-tốc độ liên quan đến target edge của mình. Nguồn: [Ultralytics YOLO26 official docs, 2026](https://docs.ultralytics.com/models/yolo26/).*

**Performance công bố (COCO val, bảng chính thức):** YOLOv8n 37.3 mAP@0.99ms (A100 TensorRT,
3.2M param) đến YOLOv8x 53.9 mAP@3.53ms (68.2M param) — biến thể n/s là ứng viên thực tế cho
Raspberry Pi 5 với ngân sách latency end-to-end <2s/xe của project. [Nguồn](https://docs.ultralytics.com/models/yolov8/)

**Liên quan đến hệ thống mình:** Đây là phiên bản mà code training trong `src/ml/` nhắm tới theo
CLAUDE.md. Các fact về C2f/decoupled-head/TAL/CIoU+DFL ở trên nên được coi là ground truth khi
viết hoặc debug config training (loss weight, `tal_topk`, `reg_max`) và khi giải thích lựa chọn
kiến trúc trong đồ án.

```bibtex
@misc{jocher2023yolov8,
  author = {Jocher, Glenn and Chaurasia, Ayush and Qiu, Jing},
  title  = {Ultralytics YOLOv8},
  year   = {2023},
  publisher = {GitHub},
  version = {8.0.0},
  howpublished = {\url{https://github.com/ultralytics/ultralytics}}
}

@inproceedings{feng2021tood,
  author    = {Feng, Chengjian and Zhong, Yujie and Gao, Yu and Scott, Matthew R. and Huang, Weilin},
  title     = {TOOD: Task-Aligned One-Stage Object Detection},
  booktitle = {Proceedings of the IEEE/CVF International Conference on Computer Vision (ICCV)},
  year      = {2021},
  eprint    = {2108.07755},
  archivePrefix = {arXiv}
}
```

---

## 4. YOLO26 (thế hệ mới nhất, ra mắt tháng 1/2026) — verify với docs chính thức

**Trích dẫn:** G. Jocher, J. Qiu, M. Liu, S. Lyu, F. C. Akyon, and M. E. Kalfaoglu, *YOLO26*,
Ultralytics, 2026. arXiv:2606.03748 (công bố 2/6/2026).
[Official model docs](https://docs.ultralytics.com/models/yolo26/) |
[arXiv](https://arxiv.org/abs/2606.03748) |
[GitHub issue thông báo bản stable](https://github.com/ultralytics/ultralytics/issues/24844)

**Tóm tắt:** YOLO26 ra mắt tháng 1/2026, là thế hệ được Ultralytics khuyến nghị hiện tại, định vị
nhanh hơn/chính xác hơn/dễ export hơn YOLO11 và YOLOv8, bao phủ detection, instance segmentation,
pose, classification, và oriented bounding box (OBB) trong một framework. Các thay đổi kiến trúc
đã verify so với YOLOv8 (**không giả định từ kiến thức YOLOv8 cũ — đã xác nhận trực tiếp với docs
chính thức và paper tháng 6/2026**):

- **Inference NMS-free, end-to-end:** thiết kế dual-head cho phép train theo kiểu gán one-to-many
  thông thường nhưng export/chạy bằng head one-to-one cho ra detection cuối cùng trực tiếp, bỏ
  bước hậu xử lý Non-Maximum Suppression riêng — giảm latency và đơn giản hóa deploy/export (liên
  quan đến path ONNX Runtime cho Pi 5 trong `edge-deploy`). [Nguồn](https://docs.ultralytics.com/models/yolo26/)
- **Bỏ DFL:** khác với Distribution Focal Loss của YOLOv8 (regression softmax 16-bin, §3), YOLO26
  bỏ DFL để có head detection nhẹ hơn với khoảng regression *không ràng buộc*, giảm độ phức tạp
  head và đơn giản hóa export ONNX/edge (không còn softmax bin rời rạc cần trace/quantize).
  [Nguồn](https://docs.ultralytics.com/models/yolo26/)
- **Optimizer MuSGD:** một optimizer hybrid SGD + "Muon" chuyển thể từ training large-language-model
  (lấy cảm hứng từ Kimi K2 của Moonshot AI), claim mang lại convergence ổn định hơn.
  [Nguồn](https://docs.ultralytics.com/models/yolo26/)
- **Progressive Loss (ProgLoss) + Small-Target-Aware Label Assignment (STAL):** thay đổi lúc
  training để dịch trọng tâm supervision về phía head lúc inference (one-to-one) và đảm bảo rõ
  ràng độ phủ anchor positive cho vật thể nhỏ — liên quan trực tiếp đến detect biển số, vì biển số
  là vật thể nhỏ so với ảnh xe/scene đầy đủ (xem §6). [Nguồn](https://docs.ultralytics.com/models/yolo26/)

**Performance công bố (COCO, chính thức):** trên 5 scale, 40.9–57.5 mAP ở latency 1.7–11.8 ms
T4-TensorRT; YOLO26n claim nhanh hơn tới **43% CPU ONNX inference** so với YOLO11n trên Intel
Xeon CPU — bằng chứng liên quan trực tiếp cho tính khả thi inference CPU-only trên edge Pi 5, dù
con số cụ thể này là benchmark trên Intel Xeon, không phải benchmark ARM/Pi 5, nên cần **verify
độc lập trên phần cứng Pi 5 thật** trước khi trích dẫn như claim riêng cho Pi trong đồ án. Export
target gồm TensorRT, ONNX, CoreML, LiteRT, và OpenVINO. [Nguồn](https://docs.ultralytics.com/models/yolo26/)

**Liên quan đến hệ thống mình:** YOLO26 là hướng nâng cấp ứng viên từ YOLOv8 cho pha
`model-optimization` (tuần 7) nhờ export NMS-free và head nhẹ hơn — cả hai đều giảm latency
inference edge, phục vụ trực tiếp mục tiêu <2s/xe. Tuy nhiên, vì độ chín ecosystem/tooling của
Ultralytics (model cộng đồng, tutorial, hướng dẫn quantization ONNX Runtime ARM bên thứ ba) sâu
hơn nhiều cho YOLOv8 tính đến thời điểm viết, lựa chọn giữa YOLOv8 và YOLO26 cho đồ án này nên là
quyết định Mode 2 (nghiên cứu tech thực tiễn), không giả định sẵn ở đây — đánh dấu là câu hỏi mở
bên dưới.

```bibtex
@misc{jocher2026yolo26,
  author = {Jocher, Glenn and Qiu, Jing and Liu, Mengyu and Lyu, Shuai and Akyon, Fatih Cagatay and Kalfaoglu, Muhammet Esat},
  title  = {YOLO26},
  year   = {2026},
  publisher = {Ultralytics},
  eprint = {2606.03748},
  archivePrefix = {arXiv}
}
```

---

## 5. Vì sao single-stage detector phù hợp deploy edge (Pi 5, <2s/xe)

**Trích dẫn (baseline two-stage):** S. Ren, K. He, R. Girshick, and J. Sun, "Faster R-CNN: Towards
Real-Time Object Detection with Region Proposal Networks," in *Advances in Neural Information
Processing Systems (NeurIPS)*, 2015. arXiv:1506.01497.
[arXiv](https://arxiv.org/abs/1506.01497) | [NeurIPS proceedings](https://papers.nips.cc/paper/5638-faster-r-cnn-towards-real-time-object-detection-with-region-proposal-networks)

**Tóm tắt:** Thiết kế two-stage của Faster R-CNN trước tiên chạy **Region Proposal Network
(RPN)** — một fully-convolutional network nhỏ dùng chung feature backbone — để đề xuất vùng vật
thể ứng viên, rồi chạy stage thứ hai classification+regression (head Fast R-CNN) trên từng
proposal. Chia sẻ feature convolutional giữa RPN và detection head khiến region proposal "gần như
miễn phí" so với Selective Search, nhưng kiến trúc về bản chất vẫn tuần tự (đề xuất, rồi phân loại
từng proposal), báo cáo ~5 FPS trên GPU cùng thời — so với thiết kế single-pass 45 FPS của YOLOv1
trên phần cứng cùng thời. [Nguồn](https://arxiv.org/abs/1506.01497)

**Đánh đổi single-stage vs two-stage cho use-case của mình:** phát hiện chung trong literature
object detection (và được tái khẳng định bởi các nghiên cứu benchmark edge gần đây) là detector
single-stage như dòng YOLO gộp việc sinh proposal và classification vào một pass, đánh đổi một
phần accuracy (lịch sử là nhiều lỗi localization hơn, theo Redmon và cộng sự 2016, §1) để lấy lợi
thế tốc độ lớn, cộng dồn có lợi trên phần cứng edge hạn chế — đây chính xác là lý do các biến thể
YOLO (không phải biến thể R-CNN) thống trị các target deploy real-time/edge như Raspberry Pi và
NVIDIA Jetson. [Nguồn: Redmon và cộng sự 2016](https://arxiv.org/abs/1506.02640v1);
bằng chứng benchmark edge hỗ trợ:
["Benchmarking YOLOv8–YOLOv12 for Real-Time Object Detection on Single-Board Computers," MDPI *Machine Learning and Knowledge Extraction*, 2026](https://www.mdpi.com/2504-4990/8/7/204)
*(đã sửa journal ngày 2026-07-19 — trước đó ghi nhầm ở đây là "J. Imaging"; xem §8)*
và ["Bridging AI and edge computing: A comprehensive benchmark of YOLO models in the Internet of Intelligent Things," ScienceDirect, 2026](https://www.sciencedirect.com/science/article/pii/S2542660526000569).
Lưu ý: nếu dùng detector two-stage cho task detect xe+biển số của project, chạy full pipeline
kiểu R-CNN hai lần mỗi frame (một lần cho xe, một lần cho vùng biển số) sẽ cộng dồn penalty
latency mỗi stage trên Pi 5 CPU-only — càng củng cố việc dùng detector YOLO single-shot, chạy một
lần cho xe và một lần (trên ROI đã crop) cho biển số, là lựa chọn phù hợp hơn model dòng two-stage
R-CNN, ngay cả trước khi áp dụng quantization.

**Liên quan đến hệ thống mình:** biện minh trực tiếp, kèm trích dẫn, cho quyết định kiến trúc đã
có sẵn trong CLAUDE.md/`alpr-pipeline` (YOLOv8/YOLO26, không phải Faster R-CNN) — có thể dùng
nguyên văn làm đoạn "vì sao YOLO" trong Tổng quan §[lựa chọn phương pháp detection].

```bibtex
@inproceedings{ren2015fasterrcnn,
  author    = {Ren, Shaoqing and He, Kaiming and Girshick, Ross and Sun, Jian},
  title     = {Faster R-CNN: Towards Real-Time Object Detection with Region Proposal Networks},
  booktitle = {Advances in Neural Information Processing Systems (NeurIPS)},
  year      = {2015},
  eprint    = {1506.01497},
  archivePrefix = {arXiv}
}
```

---

## 6. Detection vật thể nhỏ/scene dày đặc liên quan đến biển số trong ảnh xe

**Trích dẫn:** R. Zhu, Q. He, H. Jin, Y. Han, and K. Jiang, "License Plate Detection Based on
Improved YOLOv8n Network," *Electronics*, vol. 14, no. 10, p. 2065, 2025.
[MDPI](https://www.mdpi.com/2079-9292/14/10/2065)

**Tóm tắt:** Paper này nhắm đúng vào tình huống two-stage-trong-một-pipeline của mình — biển số
nhỏ, thường xiên góc, và nằm trong scene giám sát phức tạp/dày đặc so với toàn khung ảnh xe/scene.
Tác giả thiết kế lại **module C2f** của YOLOv8n, block fusion feature **SPPF**, và thêm **head
detection nhẹ dùng depthwise-separable convolution**, cộng thay CIoU bằng loss **WIoU**
(Wise-IoU) để regression bounding-box bền vững hơn trên biển số nhỏ/bị che khuất. Kết quả báo
cáo: mAP@0.5 tăng từ 90.9% (baseline YOLOv8n) lên 94.4%, precision 90.2%→92.8%, recall
82.9%→87.9%. [Nguồn](https://www.mdpi.com/2079-9292/14/10/2065)

**Vì sao vật thể nhỏ khó với detector dựa trên grid nói chung:** điều này bắt nguồn từ ràng buộc
grid-cell của YOLOv1 gốc (§1) — mỗi ô chỉ "chịu trách nhiệm" cho số lượng box/một class giới hạn,
nên vật thể nhỏ hoặc cụm sát nhau chia sẻ một ô sẽ cạnh tranh cùng một slot dự đoán; head
multi-scale của YOLOv3 (§2) và cách gán stride mịn hơn, anchor-free, dựa TAL của YOLOv8/YOLO26
(§3–4) là các fix nối tiếp cho vấn đề này. STAL của YOLO26 (Small-Target-Aware Label Assignment,
§4) được Ultralytics trình bày như hậu duệ rõ ràng, thiết kế chuyên biệt cho dòng fix này, đảm
bảo trực tiếp độ phủ anchor positive cho vật thể nhỏ thay vì chỉ dựa vào ngưỡng IoU/TAL.
[Nguồn](https://docs.ultralytics.com/models/yolo26/)

**Liên quan đến hệ thống mình:** cascade hai detector xe-rồi-biển-số trong `alpr-pipeline`
(detect xe → crop → detect biển số trong crop) né được một phần khó khăn này bằng cách cho
detector biển số input đã crop, độ phân giải tương đối cao hơn thay vì detect biển số nhỏ xíu
trong toàn khung góc rộng của bãi xe — đáng nêu rõ như một lý do thiết kế trong đồ án, cùng với
các sửa đổi WIoU/C2f/SPPF của paper này ghi chú như một hướng future-work khả dĩ nếu recall
detect biển số nhỏ/xiên góc không đủ sau khi train baseline YOLOv8n.

```bibtex
@article{zhu2025licenseplate,
  author  = {Zhu, Ruizhe and He, Qiyang and Jin, Hai and Han, Yonghua and Jiang, Kejian},
  title   = {License Plate Detection Based on Improved YOLOv8n Network},
  journal = {Electronics},
  volume  = {14},
  number  = {10},
  pages   = {2065},
  year    = {2025},
  doi     = {10.3390/electronics14102065}
}
```

---

## 7. Mở rộng 2026-07-19: verify claim YOLO26 với nguồn gốc (Q1)

**Kết luận: ĐÃ VERIFY** (kèm một điểm timeline cần lưu ý bên dưới). Cả bốn claim kiến trúc ở §4
đã được kiểm tra lại ngày 2026-07-19 trực tiếp với [docs chính thức YOLO26](https://docs.ultralytics.com/models/yolo26/) và paper arXiv.

- **Check arXiv ID:** arXiv:2606.03748 **tồn tại và khớp** — "Ultralytics YOLO26: Unified
  Real-Time End-to-End Vision Models," G. Jocher, J. Qiu, M. Liu, S. Lyu, F. C. Akyon, và
  M. E. Kalfaoglu, nộp ngày 2/6/2026. [arXiv](https://arxiv.org/abs/2606.03748). Trích dẫn §4
  (tác giả, ID, ngày) đúng như đã viết.
- **Xác nhận primary-source từ abstract paper (re-verify 2026-07-21):** ngoài docs, cả bốn claim §4
  giờ được củng cố bằng nguyên văn *abstract arXiv* — nguồn cấp cao hơn trang docs. Nguyên văn:
  *"a dual-head design for native NMS-free end-to-end inference"*; *"removes DFL entirely, yielding
  a lighter head with unconstrained regression range"*; *"MuSGD, a hybrid Muon-SGD optimizer
  adapted from large language model training"*; *"Progressive Loss, which shifts supervision toward
  the inference-time head"* và *"STAL, a label assignment strategy that guarantees positive
  coverage for small objects."* [Nguồn: abstract arXiv:2606.03748](https://arxiv.org/abs/2606.03748).
  Cụm "unconstrained regression range" và "dual-head … NMS-free" khớp chính xác diễn đạt ở §3.1/§4.
- **NMS-free / end-to-end — đã verify.** Nguyên văn docs: *"The default one-to-one detection head
  produces predictions without non-maximum suppression (NMS), simplifying deployment and reducing
  post-processing"* và *"YOLO26 is natively end-to-end by default. Predictions are generated
  directly, reducing latency and making production integration simpler."*
  [Nguồn](https://docs.ultralytics.com/models/yolo26/)
- **Bỏ DFL — đã verify.** Nguyên văn docs: *"YOLO26 removes Distribution Focal Loss (DFL),
  reducing detection-head complexity while preserving an unconstrained regression range"* —
  khớp chính xác cách diễn đạt "unconstrained regression range" ở §4.
  [Nguồn](https://docs.ultralytics.com/models/yolo26/)
- **MuSGD — đã verify.** Nguyên văn docs: *"A hybrid optimizer that combines SGD with Muon,
  adapting optimization ideas from large language model training to computer vision."*
  [Nguồn](https://docs.ultralytics.com/models/yolo26/)
- **ProgLoss + STAL — đã verify.** Nguyên văn docs: *"Progressive Loss shifts training emphasis
  toward the inference-time head, while STAL improves positive label coverage for small
  objects."* [Nguồn](https://docs.ultralytics.com/models/yolo26/). Được corroborate độc lập bởi
  một bài review kỹ thuật bên thứ ba: R. Sapkota và cộng sự, "YOLO26: Key Architectural
  Enhancements and Performance Benchmarking for Real-Time Object Detection,"
  [arXiv:2509.25164](https://arxiv.org/html/2509.25164v1) (Cornell/Kansas State), mô tả cùng bốn
  thay đổi (NMS-free, bỏ DFL, MuSGD, ProgLoss+STAL).
- **Bảng COCO chính thức (số liệu đã verify, input 640):** YOLO26n 40.9 mAP / 38.9 ms CPU ONNX;
  YOLO26s 48.6 / 87.2 ms; YOLO26m 53.1 / 220.0 ms; YOLO26l 55.0 / 286.2 ms; YOLO26x 57.5 /
  525.8 ms (CPU = Intel Xeon; T4 TensorRT 1.7–11.8 ms).
  [Nguồn](https://docs.ultralytics.com/models/yolo26/)
- **License — đã verify:** *"YOLO26 code, models, and documentation are available … under
  AGPL-3.0 and Enterprise licenses."* [Nguồn](https://docs.ultralytics.com/models/yolo26/)
- **Điểm cần lưu ý về timeline (không phải mâu thuẫn):** YOLO26 được *preview* tại YOLO Vision
  2025 (tháng 9/2025 — trang docs có mốc "Created Sep 25, 2025"), *ra mắt chính thức* ngày
  14/1/2026
  ([thông cáo ra mắt Businesswire](https://www.businesswire.com/news/home/20260114168538/en/Ultralytics-Launches-YOLO26-Setting-a-New-Global-Standard-for-Edge-First-Vision-AI)),
  với paper arXiv theo sau ngày 2/6/2026 và thông báo release-stable trên GitHub
  ([issue #24844](https://github.com/ultralytics/ultralytics/issues/24844)) vào tháng 6/2026.
  "Ra mắt tháng 1/2026" ở §4 nhất quán với ngày launch chính thức; cho đồ án, trích dẫn ngày
  launch tháng 1/2026 cho tính khả dụng và paper arXiv tháng 6/2026 làm tài liệu tham khảo học
  thuật.

![YOLO26 training pipeline with dual detection heads, STAL and ProgLoss](https://arxiv.org/html/2606.03748v1/x1.png)
*Hình: pipeline training YOLO26 — backbone/neck dùng chung nuôi hai head song song (one-to-many + one-to-one); STAL cải thiện gán label vật thể nhỏ, ProgLoss dịch trọng tâm supervision về phía head lúc inference. Nguồn: [Jocher và cộng sự, 2026, arXiv:2606.03748, Fig. 1](https://arxiv.org/abs/2606.03748).*

**Không claim nào ở §4 bị mâu thuẫn bởi các nguồn.**

---

## 8. Mở rộng 2026-07-19: Bằng chứng benchmark Raspberry Pi 5 / ARM CPU (Q2)

**Kết luận: ĐÃ VERIFY — đã có số liệu Pi 5 cụ thể, có thể trích dẫn** từ
[Raspberry Pi guide](https://docs.ultralytics.com/guides/raspberry-pi/) chính thức của
Ultralytics, mà (tính đến tháng 7/2026, ultralytics 8.4.1, Raspberry Pi OS Bookworm/Debian 12,
FP32, input 640) công bố bảng benchmark đầy đủ theo từng format cho **YOLO26n trên Raspberry
Pi 5**:

| Format | Inference Pi 5 (ms/ảnh) | mAP50-95 (benchmark set) |
|---|---|---|
| **NCNN** | **67.69** | 0.4805 |
| OpenVINO | 70.74 | 0.4818 |
| MNN | 90.89 | 0.4784 |
| **ONNX** | **130.33** | 0.4764 |
| ExecuTorch | 148.36 | 0.4764 |
| TF SavedModel | 213.58 | 0.4764 |
| TF Lite | 251.41 | 0.4764 |
| PyTorch | 302.15 | 0.4798 |
| TorchScript | 357.58 | 0.4764 |

[Nguồn: Ultralytics Raspberry Pi guide](https://docs.ultralytics.com/guides/raspberry-pi/).
Guide này chỉ benchmark YOLO26n và YOLO26s ("other model sizes are too big to run on the
Raspberry Pis") và nói rằng *"NCNN delivers the best inference performance on Raspberry Pi
devices because it is highly optimized for mobile/embedded platforms such as ARM
architecture."* Cùng trang báo cáo **YOLO26n vs YOLO11n trên Pi 5 (ONNX): 6.79 → 7.9 FPS, nhanh
hơn ≈15%** — tức YOLO11n ONNX ≈ 147 ms/ảnh trên Pi 5. YOLOv8 không được benchmark ở trang guide
hiện tại.

**Corroborate bởi peer-reviewed:** "Benchmarking YOLOv8–YOLOv12 for Real-Time Object Detection on
Single-Board Computers," *Machine Learning and Knowledge Extraction* (MDPI), vol. 8, no. 7,
art. 204, công bố 13/7/2026, DOI
[10.3390/make8070204](https://www.mdpi.com/2504-4990/8/7/204).
**SỬA §5:** paper này trước đó được trích dẫn trong note là "MDPI J. Imaging 2026" —
ISSN trong URL (2504-4990) và tiền tố DOI (`make`) xác nhận journal là *Machine
Learning and Knowledge Extraction*, không phải *J. Imaging*. Kết quả trích xuất được (site MDPI
chặn crawl full-text tự động; ở mức abstract qua
[search index](https://www.mdpi.com/2504-4990/8/7/204) và
[bản preprints.org](https://www.preprints.org/frontend/manuscript/e4a4cbb84936f03d5149859e60260894/download_pub),
đăng ngày 14/5/2026):
- Thiết bị: Raspberry Pi 4/5, Jetson Nano, Jetson Orin, LattePanda, ở nhiều power mode; metric:
  FPS, mAP, RAM usage, FLOPs, thời gian load model; dataset: COCO.
- Model nano (n) và small (s) luôn cho performance tốt nhất trên SBC; YOLOv9 đạt tới
  **2.39 FPS ở high-power mode trên Raspberry Pi 5** (không rõ framework/format cho con số này —
  có thể là native PyTorch, khớp với con số ~300 ms PyTorch trong bảng Ultralytics ở trên).
- **YOLOv10n là model hiệu quả nhất** (cân bằng tốc độ/accuracy/tài nguyên tốt nhất, FPS cao nhất
  trên các nền tảng Pi/Jetson); YOLOv8n và YOLO11n cạnh tranh tốt, đặc biệt trên thiết bị GPU.
- YOLOv8–v12 thường tiêu tốn 4–12% RAM khả dụng trên Pi 4/5 và LattePanda.

![Benchmark YOLO26n trên Raspberry Pi 5 theo từng format](https://cdn.jsdelivr.net/gh/ultralytics/assets@main/docs/raspberry-pi-yolo26-benchmarks.avif)
*Hình: tốc độ inference YOLO26n theo từng format export trên Pi 5 — NCNN nhanh nhất 67.69 ms, ONNX 130.33 ms. Nguồn: [Ultralytics Raspberry Pi Quick Start Guide, 2026](https://docs.ultralytics.com/guides/raspberry-pi/).*

![YOLO26n vs YOLO11n FPS trên Pi 5 qua ONNX](https://cdn.jsdelivr.net/gh/ultralytics/assets@main/docs/yolo26-vs-yolo11-rpi5-onnx-benchmarks.avif)
*Hình: YOLO26n vs YOLO11n throughput trên Pi 5 qua ONNX (7.9 vs 6.79 FPS, nhanh hơn ≈15% — không phải 43% của Xeon). Nguồn: [Ultralytics Raspberry Pi Quick Start Guide, 2026](https://docs.ultralytics.com/guides/raspberry-pi/).*

**Ý nghĩa cho ngân sách <2 s/xe:** với YOLO26n qua NCNN ở ~68 ms (hoặc ONNX Runtime ở ~130 ms) mỗi
lần inference 640-px trên Pi 5, cascade hai detector (pass xe + pass biển số trên crop) tốn ~136
ms (NCNN) đến ~260 ms (ONNX) — để lại hơn 1.5 s trong ngân sách 2 s cho OCR, phân loại màu, và
I/O. Vậy detection **không phải rủi ro nghẽn cổ chai** trên Pi 5 ở FP32; latency OCR nên là thứ
benchmark tiếp theo. Đây là số liệu FP32 — quantization INT8 (tuần 7) chỉ có thể cải thiện thêm.
Lưu ý cho đồ án: số liệu của Ultralytics là do vendor tự công bố; đo đạc của mình tuần 8–9 trên
Pi 5 thật vẫn là số liệu chính thức cho chương evaluation, các bảng này chỉ làm baseline
literature.

---

## 9. Mở rộng 2026-07-19: Quyết định YOLOv8 vs YOLO26 (so sánh thực tiễn Mode 2, Q3)

Toàn bộ số liệu bên dưới đã verify ngày 2026-07-19 với trang docs model chính thức
([YOLOv8](https://docs.ultralytics.com/models/yolov8/),
[YOLO11](https://docs.ultralytics.com/models/yolo11/),
[YOLO26](https://docs.ultralytics.com/models/yolo26/)) và
[Raspberry Pi guide](https://docs.ultralytics.com/guides/raspberry-pi/).

| Tiêu chí | YOLOv8 (2023) | YOLO26 (2026) |
|---|---|---|
| COCO mAP50-95 (n / s, 640) | 37.3 / 44.9 | **40.9 / 48.6** (+3.6 / +3.7) |
| CPU ONNX latency, Intel Xeon (n / s) | 80.4 / 128.4 ms | **38.9 / 87.2 ms** |
| Bằng chứng ARM Pi 5 | không có ở guide chính thức hiện tại; paper SBC peer-review cho thấy v8n cạnh tranh nhưng dưới v10n ([MAKE 2026](https://www.mdpi.com/2504-4990/8/7/204)) | **bảng Pi 5 chính thức: 67.7 ms NCNN / 130.3 ms ONNX (26n, FP32, 640)**; nhanh hơn ~15% so với YOLO11n ONNX trên Pi 5 ([guide](https://docs.ultralytics.com/guides/raspberry-pi/)) |
| Hậu xử lý NMS | bắt buộc (thêm latency + phức tạp hóa export-graph) | **không bắt buộc — end-to-end bản chất** ([docs](https://docs.ultralytics.com/models/yolo26/)) |
| Head regression | DFL, softmax 16-bin (thêm op cần export/quantize) | **không có DFL**, regression thuần — graph ONNX đơn giản hơn cho INT8 ([docs](https://docs.ultralytics.com/models/yolo26/)) |
| Format export | ONNX, NCNN, OpenVINO, TFLite, TensorRT, CoreML, … | cùng bộ (TensorRT, ONNX, CoreML, LiteRT, OpenVINO, NCNN theo Pi guide) |
| Path quantization INT8 | chín muồi, nhiều hướng dẫn bên thứ ba, nhưng NMS + DFL nằm ngoài/ở rìa graph đã quantize | ít hướng dẫn công bố hơn, nhưng graph đơn giản hơn về cấu trúc (không NMS, không DFL) — Ultralytics quảng cáo là "quantization-robust"; cần tự validate ở tuần 7 |
| Hỗ trợ vật thể nhỏ (biển số) | chỉ có gán TAL | dòng TAL **+ STAL** dành riêng cho độ phủ positive vật thể nhỏ ([docs](https://docs.ultralytics.com/models/yolo26/)) |
| Khả năng trích dẫn học thuật | không có paper — trích dẫn software ([docs FAQ](https://docs.ultralytics.com/models/yolov8/)) | **có paper arXiv**: [2606.03748](https://arxiv.org/abs/2606.03748) (chưa peer-review, nhưng trích dẫn được) |
| Ecosystem / tiền lệ ALPR | sâu: 3 năm tutorial, paper detect biển số (vd [Zhu và cộng sự 2025](https://www.mdpi.com/2079-9292/14/10/2065)) | mỏng: ra mắt tháng 1/2026; chỉ có docs/guide chính thức, ít bài viết ALPR bên thứ ba |
| License | AGPL-3.0 + Enterprise ([docs](https://docs.ultralytics.com/models/yolov8/)) | AGPL-3.0 + Enterprise ([docs](https://docs.ultralytics.com/models/yolo26/)) — giống hệt; không phải điểm khác biệt |
| API / code training | package `ultralytics` | cùng package (checkpoint tên `yolo26n.pt`) — chi phí chuyển đổi ≈ một chuỗi string |

![Latency inference end-to-end NMS-free của YOLO26 vs các model dùng NMS](https://cdn.jsdelivr.net/gh/ultralytics/assets@main/docs/Ultralytics-YOLO26-Benchmark-E2E.jpg)
*Hình: latency inference end-to-end (NMS-free) của YOLO26 so với các model dùng NMS — cho thấy lợi thế deploy của head one-to-one mặc định trên CPU/edge, trực tiếp liên quan đến target Pi 5. Nguồn: [Ultralytics YOLO26 official docs, 2026](https://docs.ultralytics.com/models/yolo26/).*

**Khuyến nghị (cho lúc bắt đầu training tuần 3, 29/07/2026):** train **YOLO26n làm detector
chính** cho cả hai giai đoạn xe và biển số, với **YOLOv8n làm baseline fallback đã train** (chạy
Colab thêm — cả hai dùng chung API `ultralytics` và format dataset y hệt, nên chi phí biên chỉ là
GPU-hours, không phải công sức engineering). Lý do: YOLO26n vượt trội YOLOv8n về accuracy (+3.6
mAP) và latency CPU (nhanh gấp 2× trên Xeon; chỉ có số liệu Pi 5 chính thức), graph NMS-free
DFL-free của nó là điểm khởi đầu tốt hơn cho công việc INT8/ONNX tuần 7, và STAL nhắm thẳng vào
sub-problem khó nhất của mình (biển số nhỏ). Train cả hai cũng cho đồ án sẵn một bảng so sánh
"lựa chọn model" cho chương evaluation.

**Rủi ro:** (1) tiền lệ ALPR bên thứ ba cho YOLO26 còn mỏng — nếu fine-tuning có hành vi bất
thường (vd MuSGD không ổn định trên dataset nhỏ tùy biến của mình), fallback về YOLOv8n, đây là
lý do run baseline là bắt buộc, không phải tùy chọn; (2) chưa có validate bên thứ ba nào công bố
về accuracy quantization post-training INT8 trên head DFL-free của YOLO26 — dành thời gian tuần 7
để tự đo mAP drop; (3) thiên lệch vendor-benchmark — tất cả số liệu tốc độ headline là của
Ultralytics tự công bố; coi là baseline literature và tự đo lại trên Pi 5 (tuần 8–9); (4)
AGPL-3.0 áp dụng cho cả hai, nên không ảnh hưởng lựa chọn, nhưng việc release code đồ án vẫn phải
tương thích open-source dù chọn bên nào.

---

## 10. Mở rộng 2026-07-19: Khoảng trống dòng dõi YOLOv9 / YOLOv10 / YOLO11 (Q4)

Lấp khoảng trống §2→§4 để đồ án có thể trình bày bảng dòng dõi v1→v26 đầy đủ.

- **YOLOv9 (Wang, Yeh, Liao, 2/2024, [arXiv:2402.13616](https://arxiv.org/abs/2402.13616)):**
  nhắm vào *mất thông tin* trong deep network thay vì thiết kế head/assignment. Đưa vào **PGI
  (Programmable Gradient Information)** — một cấu trúc supervision phụ trợ "provide[s] complete
  input information for the target task to calculate objective function, so that reliable
  gradient information can be obtained to update network weights" — và **GELAN (Generalized
  Efficient Layer Aggregation Network)**, một kiến trúc nhẹ chỉ dùng convolution thông thường mà
  "achieve[s] better parameter utilization than … methods developed based on depth-wise
  convolution." YOLOv9 train từ đầu vượt qua SOTA đã pre-trained trên MS COCO.
- **YOLOv10 (Wang và cộng sự, NeurIPS 2024, [arXiv:2405.14458](https://arxiv.org/abs/2405.14458)):**
  tổ tiên trí tuệ trực tiếp của thiết kế NMS-free của YOLO26. Abstract: "we first present the
  **consistent dual assignments for NMS-free training** of YOLOs, which brings competitive
  performance and low inference latency simultaneously" — head one-to-many supervise lúc training
  trong khi head one-to-one phục vụ inference, bỏ NMS vì "the reliance on the non-maximum
  suppression (NMS) for post-processing hampers the end-to-end deployment of YOLOs." Head
  one-to-one end-to-end mặc định của YOLO26 (§4, §7) kế thừa từ scheme này — trích dẫn YOLOv10
  trong đồ án khi giải thích nguồn gốc tính chất NMS-free của YOLO26.
- **YOLO11 (Ultralytics, 9/2024, [docs chính thức](https://docs.ultralytics.com/models/yolo11/)):**
  giống YOLOv8, một bản release software **không có paper chính thức** (docs FAQ: "Ultralytics
  has not published a formal research paper for YOLO11"); trích dẫn software (`ultralytics`
  v11.0.0, Jocher & Qiu). Về kiến trúc là một bản refresh hiệu quả của YOLOv8: backbone/neck cải
  tiến trong đó C2f được thay bằng block **C3k2** và thêm module **C2PSA** (partial spatial
  attention) sau SPPF — tên component theo overview bên thứ ba R. Khanam và M. Hussain, "YOLOv11:
  An Overview of the Key Architectural Enhancements," [arXiv:2410.17725](https://arxiv.org/abs/2410.17725)
  ("the introduction of the C3k2 (Cross Stage Partial with kernel size 2) block, SPPF … and
  C2PSA"). Kết quả chính thức: YOLO11n 39.5 mAP / 56.1 ms CPU ONNX; YOLO11m ngang bằng/vượt mAP
  YOLOv8m với **ít hơn 22% tham số**
  ([docs](https://docs.ultralytics.com/models/yolo11/)).

![YOLOv10: so sánh latency-accuracy và model size-accuracy với các detector real-time trước đó](https://arxiv.org/html/2405.14458v1/x1.png)
*Hình: YOLOv10 — trade-off latency-accuracy (trái) và kích thước model-accuracy (phải) so với các detector real-time trước đó. Thiết kế NMS-free end-to-end đạt accuracy cạnh tranh ở latency thấp hơn — pattern thiết kế YOLO26 kế thừa. Nguồn: [A. Wang và cộng sự, 2024, NeurIPS 2024, arXiv:2405.14458, Fig. 1](https://arxiv.org/abs/2405.14458).*

Câu tóm một dòng dòng dõi cho bảng đồ án: v9 = fix gradient/information lúc training (PGI+GELAN);
v10 = dual assignment NMS-free (deploy end-to-end); v11 = refresh hiệu quả (C3k2/C2PSA, ít tham
số hơn); v26 = hợp nhất ý tưởng end-to-end của v10 + bỏ DFL + gán vật thể nhỏ (STAL), tinh chỉnh
riêng cho export edge/CPU.

---

## 11. Mở rộng 2026-07-19: sanity check các claim đã đánh dấu (Q5)

- **"Nhanh hơn 43% CPU ONNX vs YOLO11n" — nguyên văn ĐÃ VERIFY, nhưng đã sửa phạm vi.** Nguyên
  văn docs: *"up to 43% faster CPU ONNX inference for YOLO26n compared with YOLO11n on an Intel
  Xeon CPU @ 2.00 GHz"* [Nguồn](https://docs.ultralytics.com/models/yolo26/). Note's caution ở
  §4 là chính đáng và giờ **đã có data trả lời**: trên phần cứng ARM Pi 5 thật, guide chính thức
  của Ultralytics chỉ đo được mức tăng **≈15% FPS** cho YOLO26n so với YOLO11n qua ONNX (6.79 →
  7.9 FPS) [Nguồn](https://docs.ultralytics.com/guides/raspberry-pi/). **Con số 43% không
  transfer sang ARM** — trong đồ án, trích 43% chặt chẽ như claim riêng Intel Xeon và ~15% như
  con số ARM/Pi 5.
- **"Ultralytics chưa từng công bố paper peer-review cho YOLOv8" — ĐÃ VERIFY, vẫn đúng tính đến
  tháng 7/2026.** Nguyên văn docs FAQ: *"Ultralytics has not published a formal research paper
  for YOLOv8 due to the rapidly evolving nature of the models"*; hướng dẫn trích dẫn là một entry
  BibTeX `@software` cho repo [Nguồn](https://docs.ultralytics.com/models/yolov8/). Tương tự cho
  YOLO11 [Nguồn](https://docs.ultralytics.com/models/yolo11/). Điểm cần thêm vào references của
  đồ án: với YOLO26, lần đầu tiên Ultralytics công bố một paper arXiv
  ([2606.03748](https://arxiv.org/abs/2606.03748)) — trích dẫn được, dù arXiv không phải
  peer-review.
- **Lỗi journal attribution đã tìm và sửa:** paper benchmark SBC trích ở §5 là "MDPI J. Imaging
  2026" thực ra thuộc *Machine Learning and Knowledge Extraction* (MAKE), vol. 8, no. 7, art.
  204, DOI 10.3390/make8070204, công bố 13/7/2026 — ISSN 2504-4990 trong URL và tiền tố DOI
  `make` xác nhận điều này. §5 đã được chú thích tại chỗ. **Cập nhật 2026-07-21 — danh sách tác giả
  ĐÃ RESOLVE** qua Crossref API (`api.crossref.org/works/10.3390/make8070204`): O. Shalash,
  E. Khatab, A. El-Agamy, L. Elmokadem, Y. Abouelsaad, J. Zaki, M. El-Sayed, H. Said (8 tác giả,
  đúng thứ tự). Placeholder trong `refs.bib` (`mdpi2026sbcbenchmark`) đã thay bằng author list
  thật. **Còn mở:** anti-bot MDPI vẫn chặn full-text nên bảng FPS Pi 5 per-model chưa lấy được ở
  mức chi tiết — xác nhận từ PDF trước khi khóa bảng số của chương evaluation.

---

## 12. Mở rộng 2026-07-21: Bằng chứng quantization INT8 cho head DFL-free của YOLO26 (Q6)

**Kết luận: TÌM ĐƯỢC bằng chứng bên thứ ba (định tính + một datapoint thực nghiệm), NHƯNG chưa có
số INT8 trên Pi 5 CPU/ONNX Runtime — tự đo tuần 7 vẫn là số chính thức của đồ án.** Đây là câu hỏi
mở tuần 7 ("chưa tìm được validate bên thứ ba nào") — pass research 2026-07-21 lấp một phần.

- **Cơ chế (vì sao head DFL-free dễ quantize hơn) — nguồn arXiv trích dẫn được.** S. Chakrabarty,
  "YOLO26: An Analysis of NMS-Free End to End Framework," [arXiv:2601.12882](https://arxiv.org/abs/2601.12882)
  (19/1/2026) nêu rõ vì sao bỏ DFL giúp INT8: nguyên văn *"On specialized edge hardware (NPUs and
  DSPs), these Softmax layers are notoriously difficult to quantize and often become the primary
  latency bottleneck."* DFL = softmax 16-bin mỗi cạnh (§3.1 bước 5); bỏ nó cắt đúng op khó
  quantize → biện minh kiến trúc trực tiếp cho việc chọn YOLO26 ở path INT8/edge của mình.
- **Claim tổng quan (định tính, không số per-variant).** R. Sapkota và M. Karkee, "Ultralytics
  YOLO Evolution," [arXiv:2510.09653](https://arxiv.org/abs/2510.09653) (6/10/2025) chỉ nói
  *"INT8 exports of YOLO26 retain nearly the same mAP as FP32 versions"* — không kèm phần trăm
  hay ablation từng scale; coi là claim tổng quan/vendor-adjacent, chưa đủ làm bằng chứng định
  lượng.
- **Datapoint thực nghiệm (GRAY LITERATURE — practitioner blog, KHÔNG peer-review).** D. Dubinsky,
  "Porting YOLO26n to the Hailo-8L,"
  [case study](https://danieldubinsky.github.io/personal-site/case-studies/yolo26n-hailo-L8/):
  INT8 accuracy retention so với FP32 baseline — **YOLO26n 92.3%, YOLO26s 88.9%, YOLO26m 84.0%,
  YOLO26l 87.4%**; cụ thể YOLO26n **mAP 0.402 (FP32) → 0.371 (INT8), drop ~7.7%**. Tác giả gán drop
  cho *"the sensitivity of the non-NMS heads to quantization noise."* Latency trên Hailo-8L:
  11.56 ms / 86.5 FPS (C++), ~13× so với baseline CPU ONNX.
- **Cảnh báo chuyển giao (bắt buộc đọc trước khi dùng số trên):**
  1. **Khác phần cứng.** Hailo-8L là NPU chuyên dụng + hybrid postproc CPU — *không phải* path Pi 5
     CPU-only + ONNX Runtime của project (CLAUDE.md). Retention INT8 phụ thuộc toolchain quantize
     (Hailo Dataflow Compiler vs ONNX Runtime static INT8) nên **các % trên KHÔNG transfer trực
     tiếp** sang Pi 5; dùng directional thôi.
  2. **Retention không đơn điệu theo size.** YOLO26m (84.0%) tệ hơn cả s (88.9%) *và* l (87.4%) —
     cảnh báo rằng không được suy "model nhỏ hơn → drop nhỏ hơn"; phải đo riêng biến thể mình deploy
     (YOLO26n cho edge).
  3. **Gray literature.** Blog cá nhân — trích như datapoint kỹ thuật có ghi rõ nguồn, KHÔNG như số
     peer-review; số chính thức của chương evaluation phải là đo của mình.
- **Ý nghĩa cho project (tuần 7):** tín hiệu tích cực — YOLO26n giữ retention cao nhất trong họ
  (~92% trên Hailo) và graph DFL-/NMS-free đơn giản hơn cho ONNX Runtime INT8. Nhưng vì head
  one-to-one NMS-free *cũng* nhạy quant noise (theo Dubinsky), tuần 7 phải benchmark **cả mAP drop
  lẫn latency** sau static INT8 trên Pi 5, không chỉ latency.

```bibtex
@misc{chakrabarty2026yolo26nmsfree,
  author = {Chakrabarty, Sudip},
  title  = {YOLO26: An Analysis of NMS-Free End to End Framework for Real-Time Object Detection},
  year   = {2026},
  eprint = {2601.12882},
  archivePrefix = {arXiv}
}

@misc{sapkota2025yoloevolution,
  author = {Sapkota, Ranjan and Karkee, Manoj},
  title  = {Ultralytics YOLO Evolution: An Overview of YOLO26, YOLO11, YOLOv8 and YOLOv5 Object Detectors for Computer Vision and Pattern Recognition},
  year   = {2025},
  eprint = {2510.09653},
  archivePrefix = {arXiv}
}

@misc{dubinsky2026yolo26hailo,
  author       = {Dubinsky, Daniel},
  title        = {Porting YOLO26n to the Hailo-8L},
  year         = {2026},
  howpublished = {\url{https://danieldubinsky.github.io/personal-site/case-studies/yolo26n-hailo-L8/}},
  note         = {Practitioner case study; INT8 retention YOLO26 n/s/m/l = 92.3/88.9/84.0/87.4\%}
}
```

---

## Câu hỏi mở / việc cần theo dõi (cập nhật 2026-07-21)

- ~~Claim tốc độ headline của YOLO26 (nhanh hơn 43% CPU ONNX vs YOLO11n) benchmark trên Intel
  Xeon CPU, không phải ARM/Raspberry Pi 5 — cần benchmark Pi 5 độc lập trước khi trích dẫn như
  claim latency edge.~~ **ĐÃ GIẢI QUYẾT (§8, §11):** guide Pi chính thức của Ultralytics giờ công
  bố số liệu Pi 5 — YOLO26n 67.69 ms NCNN / 130.33 ms ONNX ở FP32/640, và chỉ nhanh hơn ~15%
  (không phải 43%) so với YOLO11n qua ONNX trên Pi 5. Đo đạc Pi của mình tuần 8–9 vẫn cần cho
  chương evaluation, nhưng khoảng trống trích dẫn literature đã được lấp.
- ~~Train YOLOv8 hay YOLO26 là quyết định Mode 2 — khuyến nghị một note so sánh thực tiễn theo
  dõi trước tuần 3.~~ **ĐÃ GIẢI QUYẾT (§9):** khuyến nghị = YOLO26n chính + YOLOv8n
  baseline/fallback đã train; rủi ro đã ghi (tiền lệ ALPR mỏng, hành vi INT8 của head DFL-free
  chưa validate, thiên lệch vendor-benchmark).
- ~~Ultralytics chưa từng công bố paper peer-review cho YOLOv8.~~ **RE-VERIFY tính đến tháng
  7/2026 (§11):** vẫn đúng, theo docs FAQ chính thức; YOLO26 là thế hệ đầu tiên có paper arXiv
  (2606.03748).
- ~~Chưa đào sâu cơ chế YOLOv9/YOLOv10/YOLO11.~~ **ĐÃ GIẢI QUYẾT (§10):** khoảng trống dòng dõi
  đã lấp bằng trích dẫn gốc (arXiv:2402.13616, arXiv:2405.14458 — NeurIPS 2024, docs chính thức
  YOLO11 + arXiv:2410.17725).
- ~~danh sách tác giả đầy đủ của paper benchmark SBC MAKE 2026 (DOI 10.3390/make8070204).~~
  **ĐÃ GIẢI QUYẾT 2026-07-21 (§11):** 8 tác giả lấy qua Crossref (Shalash, Khatab, El-Agamy,
  Elmokadem, Abouelsaad, Zaki, El-Sayed, Said), placeholder `refs.bib` đã thay. **Còn mở phần
  nhỏ:** bảng FPS Pi 5 per-model chi tiết vẫn sau anti-bot MDPI — xác nhận từ PDF trước khi khóa
  bảng số chương evaluation.
- **VẪN CÒN MỞ (tuần 7) — thu hẹp 2026-07-21 (§12):** đã có bằng chứng bên thứ ba (mechanism:
  arXiv:2601.12882 "Softmax khó quantize"; datapoint gray-lit Hailo-8L: retention YOLO26n 92.3%,
  mAP 0.402→0.371 INT8) nhưng **chưa có số Pi 5 CPU/ONNX Runtime INT8** — hardware khác, không
  transfer. Tự đo mAP drop static-INT8 trên Pi 5 tuần 7 vẫn là số chính thức của đồ án.
- **VẪN CÒN MỞ (tuần 4+):** latency giai đoạn OCR trên Pi 5 — detection ở ~68–130 ms/pass (§8) để
  lại OCR là likely dominant latency term trong ngân sách <2 s; benchmark PaddleOCR vs EasyOCR
  trên ARM tiếp theo.

**Feeds vào:** Chương Tổng quan (Overview) — bối cảnh object detection + cơ chế forward pass
pixel→box (§3.1) + bảng dòng dõi v1→v26 đầy đủ (§10) và luận điểm "vì sao YOLO / chọn YOLO nào"
(§5, §9); chương training detector tuần 3 (train YOLO26n chính + YOLOv8n baseline, khuyến nghị §9;
tham số assigner thực tế §3); chương model-optimization tuần 7 (INT8 trên head DFL-free — bằng
chứng + cảnh báo chuyển giao ở §12, rủi ro 2 ở §9); chương edge-deployment/evaluation tuần 8–9
(bảng latency baseline literature Pi 5 ở §8, kết quả NCNN nhanh hơn ONNX). Companion HTML explainer:
`research/2026-07-19-yolo-critical-questions.html`.
