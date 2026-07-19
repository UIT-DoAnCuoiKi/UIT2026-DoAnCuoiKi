# YOLO Architecture: From Grid-Cell Regression to YOLO26 (Deep Literature Review)

Mode 1 (academic literature review) for thesis Chapter Tổng quan. Focus: mechanics of the
YOLO lineage relevant to this project's vehicle+plate detector (YOLOv8/YOLO26 via Ultralytics,
`src/ml/`), plus the single-stage-vs-two-stage rationale for Raspberry Pi 5 edge deployment.

---

## 1. Original YOLO (Redmon et al., 2016) — unifying detection into one regression

**Citation:** J. Redmon, S. Divvala, R. Girshick, and A. Farhadi, "You Only Look Once: Unified,
Real-Time Object Detection," in *Proc. IEEE Conf. Computer Vision and Pattern Recognition
(CVPR)*, 2016, pp. 779–788. arXiv:1506.02640.
[arXiv abstract](https://arxiv.org/abs/1506.02640) | [arXiv v1](https://arxiv.org/abs/1506.02640v1)

**Summary:** YOLOv1 reframes object detection as a single regression problem: the input image
is divided into an S×S grid (S=7 in the paper), and each grid cell predicts B bounding boxes
(B=2), each with 4 coordinates plus an objectness confidence score, and C class probabilities
(C=20 for PASCAL VOC) — one forward pass through a single CNN produces all detections, unlike
prior pipelines (e.g., R-CNN family) that ran a classifier repeatedly over region proposals. The
network output tensor is S×S×(B*5+C). Confidence is defined as
`Pr(Object) * IOU(pred, truth)`, and at test time class-specific confidence per box is the
product of the box confidence and the conditional class probability `Pr(Class_i|Object)`. Because
the whole pipeline is one network trained end-to-end directly on detection performance, YOLOv1
runs at 45 FPS (base) to 155 FPS (Fast YOLO), roughly double the mAP of other real-time detectors
of that era, but makes more localization errors than two-stage systems and struggles with small
objects/objects in groups because each grid cell can only predict boxes for one class and a
fixed, small number of boxes. [Source](https://arxiv.org/abs/1506.02640v1)

**Loss function structure:** the paper's training objective is a multi-part sum-of-squared-error
loss with separate weighting for localization error (`λ_coord=5`), no-object confidence error
(`λ_noobj=0.5`, downweighted since most grid cells contain no object), objectness confidence
error for cells that do contain an object, and classification error — all computed only for the
"responsible" predictor box (the one with highest IOU with ground truth in a cell). This
establishes the three loss families (box/localization, objectness/confidence, classification)
that persist conceptually through the whole YOLO lineage, even as the exact loss terms change
(see YOLOv8 below). [Source](https://arxiv.org/abs/1506.02640v1)

**Anchor-free vs anchor-based:** YOLOv1 is anchor-free (each cell directly regresses box
coordinates as offsets); anchor boxes were introduced later in YOLOv2/v3 (k-means-derived priors)
to improve recall on varied aspect ratios, then removed again in YOLOv8 (anchor-free, see §3) —
i.e., the field went anchor-free → anchor-based → anchor-free, and our detector (YOLOv8) sits on
the anchor-free side. [Source: Terven & Cordova-Esparza survey, arXiv:2304.00501]

**Relevance to our system:** This is the conceptual ancestor of YOLOv8/YOLO26, used for both
vehicle detection and plate detection stages in the ALPR pipeline (`src/ml/`, per the
`alpr-pipeline` skill contract). Useful in the thesis Tổng quan chapter as the "why single-shot
detection" origin story before explaining why we picked a modern derivative.

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

## 2. YOLOv3/v4/v5 evolution — why the architecture changed

**Citation (survey covering this span):** J. Terven and D. Cordova-Esparza, "A Comprehensive
Review of YOLO Architectures in Computer Vision: From YOLOv1 to YOLOv8 and YOLO-NAS," *Machine
Learning and Knowledge Extraction*, 2023. arXiv:2304.00501.
[arXiv abstract](https://arxiv.org/abs/2304.00501) | [HTML full text](https://arxiv.org/html/2304.00501v5)

**Summary:** This survey (36 pages, 21 figures) traces architectural motivation across versions,
used here as the secondary synthesis source cross-checked against Ultralytics' own docs.

- **YOLOv3 (Redmon & Farhadi, 2018):** introduced a 53-layer **Darknet-53** backbone with
  residual connections (replacing max-pooling with strided convolutions), giving ResNet-152-level
  top-1/top-5 accuracy at roughly 2x the speed. To fix YOLOv1/v2's weakness on small objects,
  YOLOv3 added **multi-scale prediction** at three feature-map resolutions (13×13, 26×26, 52×52
  for 416×416 input) using upsampling + concatenation across backbone stages — an early FPN-style
  design — with 3 anchor priors per scale (9 total, from k-means clustering on the training set).
  [Source](https://arxiv.org/html/2304.00501v5)
- **YOLOv4 (Bochkovskiy, Wang, Liao, 2020):** backbone became **CSPDarknet53** (Cross-Stage
  Partial connections reduce redundant gradient computation while preserving accuracy) with Mish
  activation; neck added **SPP** (spatial pyramid pooling, enlarging receptive field near-free)
  plus a modified **PANet** (concatenation instead of the original paper's addition) for
  bottom-up + top-down multi-scale feature fusion. YOLOv4 also formalized a "Bag of
  Freebies/Bag of Specials" methodology — Mosaic augmentation, DropBlock, CIoU loss, label
  smoothing (free — training-time only) vs. Mish, CSP connections, SAM (small inference-cost
  increase for accuracy gain) — as a systematic way to trade off speed vs. accuracy improvements.
  [Source](https://arxiv.org/html/2304.00501v5)
- **YOLOv5 (Ultralytics/Jocher, 2020):** reimplemented in PyTorch (vs. Darknet's C), keeping a
  CSPDarknet53-style backbone with a Focus/stem strided-conv layer to cut compute, replacing SPP
  with the faster **SPPF** module, using a modified **CSP-PAN** neck, and adding **AutoAnchor** to
  re-cluster anchor boxes automatically per custom dataset. Still anchor-based and still a coupled
  detection head at this point. Ships as five scaled variants (n/s/m/l/x) that vary network
  width/depth — the same width/depth scaling convention YOLOv8 (and this project's models)
  inherit. [Source](https://arxiv.org/html/2304.00501v5); backbone/neck also cross-checked against
  [Ultralytics YOLOv5 docs](https://docs.ultralytics.com/models/yolov5/) and
  [YOLOv5 architecture tutorial](https://docs.ultralytics.com/yolov5/tutorials/architecture-description/).

**Net effect across v3→v5:** each generation traded increasing backbone/neck sophistication
(residual → CSP connections, single-scale → multi-scale FPN/PANet fusion) for better small-object
recall and training efficiency, while keeping the core "grid + anchor boxes + objectness" head
design essentially unchanged until YOLOv8 broke from it. [Source: arXiv:2304.00501]

**Relevance to our system:** Explains *why* YOLOv8's backbone/neck exist in their current form —
they are direct descendants of the CSP+PAN lineage, not a clean-slate design. Useful as brief
lineage context in Tổng quan before the YOLOv8 deep-dive.

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

## 3. YOLOv8 (Ultralytics) — the version our training code depends on

**Citation:** G. Jocher, A. Chaurasia, and J. Qiu, *Ultralytics YOLOv8* (software), version
8.0.0, 2023. [GitHub](https://github.com/ultralytics/ultralytics) |
[Official model docs](https://docs.ultralytics.com/models/yolov8/) |
[Architecture guide](https://docs.ultralytics.com/guides/yolo-architecture/). Ultralytics has
**not** published a formal peer-reviewed paper for YOLOv8 — the GitHub repo + docs site is the
canonical, citable source; architectural claims below are cross-checked between the official
`yolo-architecture` guide page and the Terven & Cordova-Esparza survey (§2 citation), which
independently describes the same components. [Source](https://docs.ultralytics.com/models/yolov8/)

**Summary of mechanics (backbone → neck → head → loss → label assignment):**

- **Backbone (CSPDarknet variant):** multi-scale feature extraction at strides 8/16/32
  (feature maps P3, P4, P5), built from stacked **C2f** blocks ("CSP Bottleneck with 2
  convolutions, faster") and a final **SPPF** block. C2f replaces YOLOv5's **C3** module: instead
  of routing only the final bottleneck output into the fusion convolution, C2f concatenates *all*
  `n+2` intermediate feature tensors along the split-and-bottleneck path before the final 1×1 conv
  — giving richer gradient flow and feature reuse without materially raising compute, at the cost
  of slightly higher activation memory than C3.
  [Source](https://docs.ultralytics.com/guides/yolo-architecture/)
- **Neck (PAN-FPN):** fuses the P3/P4/P5 backbone features top-down and bottom-up (Path
  Aggregation Network on top of a Feature Pyramid), same topological role as YOLOv4/v5's
  PANet/CSP-PAN but rebuilt with C2f blocks instead of C3. [Source](https://docs.ultralytics.com/guides/yolo-architecture/)
- **Anchor-free, decoupled head:** YOLOv8 drops anchor boxes entirely — it is a "natively
  anchor-free" detector, eliminating the need to hand-tune anchor priors per dataset (relevant
  since our two object classes, vehicles and plates, have very different aspect-ratio
  distributions). The detection head is **decoupled**: two parallel branches per pyramid level,
  one predicting box regression (`4 * reg_max` channels, `reg_max=16` by default) and one
  predicting per-class scores, rather than one shared branch predicting objectness+class+box
  together as in v1–v5. Decoupling reduces gradient interference between the classification and
  localization objectives. [Source](https://docs.ultralytics.com/guides/yolo-architecture/) and
  [Source](https://arxiv.org/html/2304.00501v5)
- **Task-Aligned Assigner (TAL) for label assignment:** YOLOv8's training-time positive/negative
  sample assignment is based on **TOOD's Task Alignment Learning** (Feng et al., ICCV 2021), not
  a hand-designed IoU threshold rule. Ultralytics' `TaskAlignedAssigner`
  (`ultralytics/utils/tal.py`) scores each anchor point by a task-alignment metric
  `t = s^alpha * u^beta` combining classification score `s` and IoU `u` between predicted and
  ground-truth boxes, with default `alpha=0.5`, `beta=6.0`, selecting the **top-k** (default
  `topk=10`) aligned anchors per ground-truth object as positives — explicitly designed to
  reduce the classification/localization misalignment that plagued earlier coupled, IoU-threshold
  based assignment. [Source: TOOD paper](https://arxiv.org/abs/2108.07755) |
  [Source: Ultralytics loss.py](https://github.com/ultralytics/ultralytics/blob/main/ultralytics/utils/loss.py) |
  [Source: Ultralytics loss API docs](https://docs.ultralytics.com/reference/utils/loss/)
- **Loss composition:** total loss = box loss (**CIoU** — Complete IoU, penalizing center
  distance and aspect-ratio mismatch in addition to overlap) + **DFL** (Distribution Focal Loss,
  regressing each box edge as a discrete probability distribution over `reg_max=16` bins via
  softmax and taking the expectation, rather than a single scalar — improves localization of
  ambiguous/small-object boundaries) + **BCE** (binary cross-entropy) for classification, applied
  only over the TAL-selected positive anchors. [Source](https://docs.ultralytics.com/guides/yolo-architecture/)
  and [Source](https://arxiv.org/html/2304.00501v5)

**Reported performance (COCO val, official table):** YOLOv8n 37.3 mAP@0.99ms (A100 TensorRT,
3.2M params) up to YOLOv8x 53.9 mAP@3.53ms (68.2M params) — the n/s variants are the practical
candidates for Raspberry Pi 5 given the project's <2s/vehicle end-to-end latency budget.
[Source](https://docs.ultralytics.com/models/yolov8/)

**Relevance to our system:** This is the version the training code in `src/ml/` targets per
CLAUDE.md. The C2f/decoupled-head/TAL/CIoU+DFL facts above should be treated as ground truth when
writing or debugging training config (loss weights, `tal_topk`, `reg_max`) and when explaining
architecture choices in the thesis.

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

## 4. YOLO26 (newest generation, released Jan 2026) — verified against official docs

**Citation:** G. Jocher, J. Qiu, M. Liu, S. Lyu, F. C. Akyon, and M. E. Kalfaoglu, *YOLO26*,
Ultralytics, 2026. arXiv:2606.03748 (published 2 June 2026).
[Official model docs](https://docs.ultralytics.com/models/yolo26/) |
[arXiv](https://arxiv.org/abs/2606.03748) |
[GitHub issue announcing stable release](https://github.com/ultralytics/ultralytics/issues/24844)

**Summary:** YOLO26 was released January 2026 as Ultralytics' current recommended generation,
positioned as faster/more accurate/more export-friendly than YOLO11 and YOLOv8, spanning
detection, instance segmentation, pose, classification, and oriented bounding boxes (OBB) in one
framework. Verified architectural changes vs. YOLOv8 (**do not assume from YOLOv8 knowledge —
confirmed directly against the official docs and the June 2026 paper**):

- **NMS-free, end-to-end inference:** a dual-head design lets the model be trained with the usual
  one-to-many assignment but exported/run with a one-to-one head that emits final detections
  directly, removing the separate Non-Maximum Suppression post-processing step — reduces latency
  and simplifies deployment/export (relevant for the Pi 5 ONNX Runtime path in `edge-deploy`).
  [Source](https://docs.ultralytics.com/models/yolo26/)
- **DFL removed:** unlike YOLOv8's Distribution Focal Loss (16-bin softmax regression, §3), YOLO26
  drops DFL for a lighter detection head with an *unconstrained* regression range, reducing head
  complexity and simplifying ONNX/edge export (no discrete-bin softmax to trace/quantize).
  [Source](https://docs.ultralytics.com/models/yolo26/)
- **MuSGD optimizer:** a hybrid SGD + "Muon" optimizer adapted from large-language-model training
  (inspired by Moonshot AI's Kimi K2), claimed to bring more stable convergence.
  [Source](https://docs.ultralytics.com/models/yolo26/)
- **Progressive Loss (ProgLoss) + Small-Target-Aware Label Assignment (STAL):** training-time
  changes that shift supervision emphasis toward the inference-time (one-to-one) head and
  explicitly guarantee positive-anchor coverage for small objects — directly relevant to plate
  detection, since plates are a small object relative to full vehicle/scene images (see §6).
  [Source](https://docs.ultralytics.com/models/yolo26/)

**Reported performance (COCO, official):** across 5 scales, 40.9–57.5 mAP at 1.7–11.8 ms
T4-TensorRT latency; YOLO26n claims up to **43% faster CPU ONNX inference** than YOLO11n on an
Intel Xeon CPU — directly relevant evidence for CPU-only edge inference feasibility on Pi 5, though
this specific number is an Intel Xeon benchmark, not an ARM/Pi 5 benchmark, so it should be
**verified independently on the actual Pi 5 hardware** before being cited as a Pi-specific claim
in the thesis. Export targets include TensorRT, ONNX, CoreML, LiteRT, and OpenVINO.
[Source](https://docs.ultralytics.com/models/yolo26/)

**Relevance to our system:** YOLO26 is a candidate upgrade path from YOLOv8 for the
`model-optimization` phase (Week 7) given its NMS-free export and lighter head — both reduce
edge-inference latency, directly serving the <2s/vehicle target. However, since Ultralytics
tooling/ecosystem maturity (community models, tutorials, third-party ONNX Runtime ARM
quantization guides) is much deeper for YOLOv8 as of this writing, the choice between YOLOv8 and
YOLO26 for this thesis should be a Mode 2 (practical tech research) decision, not assumed here —
flagged as an open question below.

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

## 5. Why single-stage detectors fit edge deployment (Pi 5, <2s/vehicle)

**Citation (two-stage baseline):** S. Ren, K. He, R. Girshick, and J. Sun, "Faster R-CNN: Towards
Real-Time Object Detection with Region Proposal Networks," in *Advances in Neural Information
Processing Systems (NeurIPS)*, 2015. arXiv:1506.01497.
[arXiv](https://arxiv.org/abs/1506.01497) | [NeurIPS proceedings](https://papers.nips.cc/paper/5638-faster-r-cnn-towards-real-time-object-detection-with-region-proposal-networks)

**Summary:** Faster R-CNN's two-stage design first runs a **Region Proposal Network (RPN)** — a
small fully-convolutional network sharing backbone features — to propose candidate object regions,
then runs a second classification+regression stage (Fast R-CNN head) on each proposal. Sharing
convolutional features between the RPN and detection head made region proposals "nearly
cost-free" compared to Selective Search, but the architecture is still fundamentally serial
(propose, then classify each proposal), reported at ~5 FPS on a contemporary GPU — versus YOLOv1's
45 FPS single-pass design on similar-era hardware. [Source](https://arxiv.org/abs/1506.01497)

**Single-stage vs two-stage tradeoff for our use case:** the general finding across the object
detection literature (and reaffirmed by recent edge-benchmarking work) is that single-stage
detectors like the YOLO family collapse proposal generation and classification into one pass,
trading some accuracy (historically, more localization error, per Redmon et al. 2016, §1) for a
large speed advantage that compounds favorably on constrained edge hardware — this is exactly why
YOLO variants (not R-CNN variants) dominate real-time/edge deployment targets such as Raspberry Pi
and NVIDIA Jetson. [Source: Redmon et al. 2016](https://arxiv.org/abs/1506.02640v1);
supporting edge-benchmark evidence:
["Benchmarking YOLOv8–YOLOv12 for Real-Time Object Detection on Single-Board Computers," MDPI J. Imaging, 2026](https://www.mdpi.com/2504-4990/8/7/204)
and ["Bridging AI and edge computing: A comprehensive benchmark of YOLO models in the Internet of Intelligent Things," ScienceDirect, 2026](https://www.sciencedirect.com/science/article/pii/S2542660526000569).
Note: for a two-stage detector on our project's own vehicle+plate detection task, running a
full R-CNN-style pipeline twice per frame (once for vehicle, once for plate region) would compound
the per-stage latency penalty on a CPU-only Pi 5 — reinforcing that a single-shot YOLO detector,
run once for vehicle and once (on the cropped ROI) for plate, is the better fit than a two-stage
R-CNN family model, even before quantization is applied.

**Relevance to our system:** direct justification, with citations, for the architecture decision
already baked into CLAUDE.md/`alpr-pipeline` (YOLOv8/YOLO26, not Faster R-CNN) — usable verbatim
as the "why YOLO" paragraph in Tổng quan §[detection method selection].

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

## 6. Small-object / dense-scene detection relevant to license plates in vehicle images

**Citation:** R. Zhu, Q. He, H. Jin, Y. Han, and K. Jiang, "License Plate Detection Based on
Improved YOLOv8n Network," *Electronics*, vol. 14, no. 10, p. 2065, 2025.
[MDPI](https://www.mdpi.com/2079-9292/14/10/2065)

**Summary:** This paper targets exactly our two-stage-within-one-pipeline scenario — plates are
small, often oblique, and embedded in complex/dense surveillance scenes relative to the full
vehicle/scene frame. The authors redesign YOLOv8n's **C2f module**, its **SPPF** feature-fusion
block, and add a **lightweight detection head using depthwise-separable convolution**, plus
replace CIoU with **WIoU** (Wise-IoU) loss for more robust bounding-box regression on
small/occluded plates. Reported results: mAP@0.5 rises from 90.9% (baseline YOLOv8n) to 94.4%,
precision 90.2%→92.8%, recall 82.9%→87.9%. [Source](https://www.mdpi.com/2079-9292/14/10/2065)

**Why small objects are hard for grid-based detectors generally:** this traces back to the
original YOLOv1 grid-cell constraint (§1) — each cell can only be "responsible" for a limited
number of boxes/one class, so small or tightly clustered objects sharing a cell compete for the
same prediction slot; YOLOv3's multi-scale heads (§2) and YOLOv8/YOLO26's finer-stride,
anchor-free, TAL-based assignment (§3–4) were successive fixes for this. YOLO26's STAL
(Small-Target-Aware Label Assignment, §4) is presented by Ultralytics as an explicit,
purpose-built successor to this line of fixes, directly guaranteeing positive-anchor coverage for
small objects rather than relying on IoU/TAL thresholds alone.
[Source](https://docs.ultralytics.com/models/yolo26/)

**Relevance to our system:** the vehicle-then-plate two-detector cascade in `alpr-pipeline`
(detect vehicle → crop → detect plate within crop) sidesteps some of this difficulty by giving the
plate detector a cropped, higher-relative-resolution input rather than detecting tiny plates in a
full wide-angle parking-lot frame — worth stating explicitly as a design rationale in the thesis,
with this paper's WIoU/C2f/SPPF modifications noted as a possible future-work direction if
plate-detection recall on small/oblique plates is insufficient after baseline YOLOv8n training.

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

## Open questions / follow-ups

- YOLO26's headline speed claims (43% faster CPU ONNX vs YOLO11n) are benchmarked on an Intel
  Xeon CPU, not ARM/Raspberry Pi 5 — needs an independent Pi 5 benchmark before citing as an edge
  latency claim (belongs in Week 7/8 `edge-deploy` benchmarking, not assumed in the overview
  chapter).
- Whether to train on YOLOv8 or YOLO26 for the thesis is a **Mode 2 (practical tech research)**
  decision (ecosystem maturity, ARM export tooling stability, community precedent for ALPR use
  cases) — not resolved by this literature review; recommend a follow-up practical-comparison note
  before Week 3 detector training starts.
- Ultralytics has never published a peer-reviewed paper for YOLOv8 (confirmed via official docs);
  the GitHub repo + docs site is the only citable primary source — flag this explicitly in the
  thesis references section rather than citing YOLOv8 as if it were a conventional paper.
- Did not deep-dive YOLOv9/YOLOv10/YOLO11 mechanics (out of scope per task instructions, since this
  project uses YOLOv8/YOLO26) — if the thesis literature review chapter wants a complete v1–v26
  lineage table for completeness, a follow-up note should fill those gaps.

**Feeds into:** Chapter Tổng quan (Overview) — object detection background section, and indirectly
the Week 3 detector-training chapter and Week 7 model-optimization chapter (YOLOv8 vs YOLO26
choice, TAL/loss hyperparameters, edge-latency rationale).
