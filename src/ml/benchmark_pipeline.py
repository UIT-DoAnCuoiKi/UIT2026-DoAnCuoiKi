"""Đo hiệu năng suy luận trên CPU: từng model ONNX riêng lẻ, từng bước trong
pipeline, và toàn pipeline end-to-end. Mọi số hiệu năng trong
docs/report/chapters/05-phanloai.md mục 5.6 đều sinh ra từ file này.

CÁCH ĐO (viết rõ ở đây để tái lập và để đối chiếu khi bảo vệ):

1. Đồng hồ: `time.perf_counter()` (đồng hồ đơn điệu, độ phân giải cao) đo thời
   gian ĐỒNG HỒ TƯỜNG, tức thời gian người dùng thật sự phải chờ. Riêng phần
   chẩn đoán tranh chấp luồng dùng thêm `time.process_time()` (tổng CPU-time của
   mọi luồng): tỉ số process_time/perf_counter cho biết pipeline đang trải công
   việc ra bao nhiêu luồng, con số này mới lộ ra vấn đề toả luồng quá mức.

2. Làm nóng (warm-up): bỏ N_WARMUP lượt chạy đầu KHÔNG tính vào kết quả. Lượt
   đầu tiên luôn chậm bất thường vì phải nạp trọng số từ đĩa, cấp phát bộ nhớ
   và chọn kernel CPU (đo được: lượt đầu ~615ms so với ~10ms các lượt sau cho
   riêng bước định vị xe). Không bỏ warm-up thì trung bình bị lệch hoàn toàn.

3. Thống kê: báo cáo TRUNG VỊ của N_RUNS lượt, không phải trung bình, vì máy
   dev có tiến trình nền (trình duyệt, IDE) thỉnh thoảng chen vào làm một vài
   lượt tăng vọt; trung vị không bị các điểm ngoại lai đó kéo lệch. In kèm min
   và max để thấy độ dao động thật.

4. Phạm vi đo: mỗi số chỉ tính phần tính toán của pipeline. KHÔNG tính thời
   gian đọc ảnh từ đĩa (`cv2.imread` chạy trước vòng đo), KHÔNG tính HTTP, mã
   hoá ảnh, ghi cơ sở dữ liệu của backend. Muốn biết độ trễ đầu-cuối mà nhân
   viên cảm nhận ở màn Trạm cổng thì cộng thêm các phần đó (đo riêng bằng
   `curl` với `POST /captures/infer`, xem README backend).

5. Ảnh dùng để đo: mặc định là ảnh mẫu commit sẵn trong repo để ai chạy cũng ra
   cùng điều kiện. Thời gian phụ thuộc nội dung ảnh (số biển phát hiện được,
   kích thước ảnh), nên khi báo cáo phải nói rõ đo trên ảnh nào.

6. Số luồng: điều khiển bằng biến môi trường ML_INTRAOP_THREADS (xem
   pipeline/onnx_pipeline.py). Script in ra giá trị đang dùng vì cùng một máy,
   đổi số luồng cho kết quả chênh nhau hơn 2 lần.

Chạy:
  python src/ml/benchmark_pipeline.py
  ML_INTRAOP_THREADS=4 python src/ml/benchmark_pipeline.py
  python src/ml/benchmark_pipeline.py --image duong/dan/anh.jpg --runs 20

Chạy trên Raspberry Pi (việc còn tồn, xem w7-onnx.md mục 2.3):
  # Pi chỉ 4 lõi, đo lần lượt vài mức để tìm giá trị tốt nhất thay vì đoán
  for n in 1 2 4; do ML_INTRAOP_THREADS=$n python src/ml/benchmark_pipeline.py; done

  # Nếu trên Pi KHÔNG cài torch/ultralytics: trỏ bước định vị xe sang bản .onnx
  # để chạy onnxruntime thuần (xem predict_vehicle.CoarseVehicleDetector).
  ML_COARSE_WEIGHTS=src/ml/weights/yolov8n.onnx python src/ml/benchmark_pipeline.py

  Lưu ý khi so sánh với số đo trên máy dev: phải dùng ĐÚNG ảnh mặc định của
  script (ảnh mẫu commit trong repo), vì thời gian phụ thuộc số biển số phát
  hiện được trên ảnh. Nên đo thêm lúc máy đã chạy nóng một lúc: Pi tự giảm
  xung nhịp khi nóng nên lần chạy đầu tiên lúc nguội thường đẹp hơn thực tế.
"""
from __future__ import annotations

import argparse
import os
import platform
import statistics
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ML_DIR = REPO_ROOT / "src" / "ml"
for _p in (ML_DIR, ML_DIR / "training", ML_DIR / "plate_detection_pipeline", ML_DIR / "plate_color_pipeline"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

DEFAULT_IMAGE = REPO_ROOT / "docs" / "research" / "assets" / "dataset-samples" / "1_bomaich_detect.png"
DEFAULT_PLATE_WEIGHTS = ML_DIR / "plate_detection_pipeline" / "weights" / "yolov8n_a1_640.onnx"

N_WARMUP = 3
N_RUNS = 10

# Các model ONNX đo riêng lẻ. Đầu vào là tensor ngẫu nhiên đúng shape: chỉ đo
# chi phí tính toán của đồ thị, không phụ thuộc nội dung ảnh.
STANDALONE_MODELS = [
    ("Phát hiện biển (YOLOv8n)", DEFAULT_PLATE_WEIGHTS),
    ("OCR biển số (CRNN)", ML_DIR / "weights" / "plate-ocr-crnn.onnx"),
    ("Loại xe (ResNet18)", ML_DIR / "weights" / "vehicle-type-resnet18.onnx"),
    ("Loại xe (MobileNetV3-Small)", ML_DIR / "weights" / "vehicle-type-mobilenet_v3_small.onnx"),
    ("Kiểu dáng xe (ResNet18)", ML_DIR / "weights" / "vehicle-style-resnet18.onnx"),
]


def _stats_ms(samples: list[float]) -> tuple[float, float, float]:
    """Trả (trung vị, min, max) tính bằng mili giây."""
    ms = sorted(s * 1000 for s in samples)
    return statistics.median(ms), ms[0], ms[-1]


def _timeit(fn, n_warmup: int = N_WARMUP, n_runs: int = N_RUNS) -> tuple[float, float, float]:
    for _ in range(n_warmup):
        fn()
    samples = []
    for _ in range(n_runs):
        t0 = time.perf_counter()
        fn()
        samples.append(time.perf_counter() - t0)
    return _stats_ms(samples)


def print_environment(threads: int) -> None:
    import cv2
    import numpy as np
    import onnxruntime as ort

    print("=" * 78)
    print("MÔI TRƯỜNG ĐO")
    print("=" * 78)
    print(f"  Máy          : {platform.processor() or platform.machine()}")
    print(f"  Số lõi logic : {os.cpu_count()}")
    print(f"  Hệ điều hành : {platform.system()} {platform.release()} (build {platform.version()})")
    print(f"  Python       : {platform.python_version()}")
    print(f"  onnxruntime  : {ort.__version__}  providers={ort.get_available_providers()}")
    print(f"  numpy/opencv : {np.__version__} / {cv2.__version__}")
    try:
        import torch

        print(f"  torch        : {torch.__version__} (chỉ dùng cho nhánh ultralytics + tiền xử lý)")
    except ImportError:
        print("  torch        : không cài (pipeline vẫn chạy nếu bước định vị dùng backend onnx)")
    print(f"  ML_INTRAOP_THREADS = {threads}  (số luồng mỗi model được phép dùng)")
    print(f"  Warm-up {N_WARMUP} lượt (bỏ), đo {N_RUNS} lượt, báo cáo TRUNG VỊ")
    print()


def bench_standalone_models(threads: int) -> None:
    """Đo từng model ONNX một mình: chỉ đồ thị tính toán, đầu vào ngẫu nhiên.

    Con số ở đây KHÔNG cộng lại thành thời gian pipeline: chạy một mình thì mỗi
    model được dùng trọn số luồng cấu hình, còn trong pipeline chúng chạy nối
    tiếp và chia nhau tài nguyên (xem bench_pipeline_stages)."""
    import numpy as np
    import onnxruntime as ort

    print("=" * 78)
    print("1. TỪNG MODEL ONNX CHẠY RIÊNG (đầu vào ngẫu nhiên đúng shape)")
    print("=" * 78)
    print(f"  {'Model':32s} {'Đầu vào':18s} {'MB':>6s} {'Trung vị':>9s} {'min':>7s} {'max':>7s}")
    so = ort.SessionOptions()
    so.intra_op_num_threads = threads
    so.inter_op_num_threads = 1
    for label, path in STANDALONE_MODELS:
        if not path.exists():
            print(f"  {label:32s} KHÔNG THẤY FILE: {path}")
            continue
        sess = ort.InferenceSession(str(path), sess_options=so, providers=["CPUExecutionProvider"])
        inp = sess.get_inputs()[0]
        shape = [d if isinstance(d, int) else 1 for d in inp.shape]
        x = np.random.rand(*shape).astype(np.float32)
        med, lo, hi = _timeit(lambda: sess.run(None, {inp.name: x}))
        size_mb = path.stat().st_size / 1e6
        print(f"  {label:32s} {str(shape):18s} {size_mb:6.1f} {med:8.2f}ms {lo:6.2f} {hi:6.2f}")
    print()


def bench_pipeline_stages(image_path: Path, plate_weights: Path, threads: int) -> None:
    """Đo từng bước bên trong pipeline thật, trên cùng một ảnh, cùng một tiến
    trình. Đây mới là con số phản ánh đúng chi phí lúc chạy thật."""
    import cv2
    import numpy as np
    from PIL import Image

    from pipeline.ocr import read_plate
    from pipeline.onnx_pipeline import OnnxAlprPipeline
    from plate_color import process_plate
    from predict_vehicle import detect_vehicle_crop

    img_bgr = cv2.imread(str(image_path))
    if img_bgr is None:
        raise FileNotFoundError(f"Không đọc được ảnh: {image_path}")

    pipe = OnnxAlprPipeline(plate_weights=str(plate_weights))
    for _ in range(N_WARMUP):
        pipe.run(img_bgr)

    print("=" * 78)
    print("2. TỪNG BƯỚC TRONG PIPELINE THẬT")
    print("=" * 78)
    print(f"  Ảnh: {image_path.name}  ({img_bgr.shape[1]}x{img_bgr.shape[0]} px)")
    n_plates = len(pipe.run(img_bgr)["plates"])
    print(f"  Số biển phát hiện được trên ảnh này: {n_plates}")
    print()

    stages: dict[str, list[float]] = {}

    def record(name: str, seconds: float) -> None:
        stages.setdefault(name, []).append(seconds)

    for _ in range(N_RUNS):
        t0 = time.perf_counter()
        img_pil = Image.fromarray(cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB))
        t1 = time.perf_counter()
        record("Chuyển màu BGR sang RGB", t1 - t0)

        dets = pipe._plate_detector.detect(img_bgr)
        t2 = time.perf_counter()
        record("Phát hiện biển số (ONNX)", t2 - t1)

        for det in dets:
            appearance = process_plate(det.crop)
            read_plate(appearance.crop_for_ocr, pipe._ocr, layout=det.cls_name)
        t3 = time.perf_counter()
        record(f"Màu biển + OCR ({n_plates} biển)", t3 - t2)

        crop_pil, det_info = detect_vehicle_crop(img_pil, detector=pipe._coarse_detector)
        t4 = time.perf_counter()
        record("Định vị + cắt vùng xe (YOLO)", t4 - t3)

        x = pipe._style_transform(img_pil).unsqueeze(0).numpy()
        t5 = time.perf_counter()
        record("Tiền xử lý ảnh cho classifier", t5 - t4)

        if pipe._type_sess is not None:
            pipe._type_sess.run(None, {pipe._type_input: x})
        t6 = time.perf_counter()
        record("Phân loại loại xe (ONNX)", t6 - t5)

        if det_info is not None and pipe._style_sess is not None:
            xs = pipe._style_transform(crop_pil).unsqueeze(0).numpy()
            pipe._style_sess.run(None, {pipe._style_input: xs})
        t7 = time.perf_counter()
        record("Phân loại kiểu dáng (ONNX)", t7 - t6)

    print(f"  {'Bước':34s} {'Trung vị':>9s} {'min':>8s} {'max':>8s} {'Tỉ lệ':>7s}")
    tong = sum(statistics.median(v) for v in stages.values()) * 1000
    for name, samples in stages.items():
        med, lo, hi = _stats_ms(samples)
        print(f"  {name:34s} {med:8.1f}ms {lo:7.1f} {hi:7.1f} {med / tong:6.1%}")
    print(f"  {'TỔNG (cộng trung vị các bước)':34s} {tong:8.1f}ms")
    print()


def bench_end_to_end(image_path: Path, plate_weights: Path, threads: int) -> None:
    """Đo `OnnxAlprPipeline.run()` như backend/edge gọi thật, kèm tỉ số CPU-time
    trên wall-time để phát hiện tình trạng toả luồng quá mức."""
    import cv2

    from pipeline.onnx_pipeline import OnnxAlprPipeline

    img_bgr = cv2.imread(str(image_path))
    pipe = OnnxAlprPipeline(plate_weights=str(plate_weights))

    t_load0 = time.perf_counter()
    pipe.run(img_bgr)
    t_first = (time.perf_counter() - t_load0) * 1000

    for _ in range(N_WARMUP):
        pipe.run(img_bgr)

    wall, cpu = [], []
    for _ in range(N_RUNS):
        w0, c0 = time.perf_counter(), time.process_time()
        pipe.run(img_bgr)
        wall.append(time.perf_counter() - w0)
        cpu.append(time.process_time() - c0)

    med_w, lo_w, hi_w = _stats_ms(wall)
    med_c, _, _ = _stats_ms(cpu)
    print("=" * 78)
    print("3. TOÀN PIPELINE (đúng cách backend và edge worker gọi)")
    print("=" * 78)
    print(f"  Lượt đầu tiên (gồm nạp model từ đĩa) : {t_first:8.1f} ms")
    print(f"  Sau khi làm nóng, trung vị            : {med_w:8.1f} ms   (min {lo_w:.1f}, max {hi_w:.1f})")
    print(f"  CPU-time trung vị / 1 ảnh             : {med_c:8.1f} ms")
    print(f"  Số luồng dùng trung bình (CPU/wall)   : {med_c / med_w:8.1f}")
    print()
    print("  Đọc chỉ số cuối: bằng ~1 nghĩa là chạy gần như đơn luồng. Càng lớn")
    print("  hơn số lõi thật thì càng có dấu hiệu toả luồng quá mức: từng đo được")
    print("  tỉ số ~24 (CPU-time ~21 giây cho 1 ảnh trong ~0,9 giây đồng hồ),")
    print("  nguyên nhân là mỗi model tự phân luồng theo toàn bộ số lõi của máy.")
    print()


def main() -> None:
    global N_RUNS, N_WARMUP

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--image", type=Path, default=DEFAULT_IMAGE, help="Ảnh dùng để đo")
    parser.add_argument("--plate-weights", type=Path, default=DEFAULT_PLATE_WEIGHTS)
    parser.add_argument("--runs", type=int, default=N_RUNS, help=f"Số lượt đo (mặc định {N_RUNS})")
    parser.add_argument("--warmup", type=int, default=N_WARMUP, help=f"Số lượt làm nóng (mặc định {N_WARMUP})")
    args = parser.parse_args()

    N_RUNS, N_WARMUP = args.runs, args.warmup

    from pipeline.onnx_pipeline import _intra_op_threads

    threads = _intra_op_threads()
    print_environment(threads)
    bench_standalone_models(threads)
    bench_pipeline_stages(args.image, args.plate_weights, threads)
    bench_end_to_end(args.image, args.plate_weights, threads)


if __name__ == "__main__":
    main()
