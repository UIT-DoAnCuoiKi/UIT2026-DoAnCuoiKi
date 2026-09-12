"""So sánh model OCR TRƯỚC và SAU khi bổ sung ký tự "Đ", trên đúng các biển có Đ.

Vì sao cần script này: báo cáo tuần 7 nêu con số cho nhóm biển MĐ/TĐ nhưng phần
phân tích đó chạy tay rồi bỏ, không có file nào trong repo dựng lại được. Script
này tái lập, xuất CSV từng biển và một ảnh ghép trước/sau để đưa vào báo cáo.

Hai model:
  - TRƯỚC: `plate-ocr-crnn-V3_seed42.pt`, charset 36 ký tự (0-9, A-Z), không có Đ.
    Model này KHÔNG THỂ đọc đúng biển MĐ/TĐ dù ảnh rõ tới đâu, vì lớp ký tự đó
    không tồn tại trong đầu ra. Nó rớt hẳn Đ chứ không đọc nhầm thành ký tự khác.
  - SAU: `plate-ocr-crnn.pt`, charset 37 ký tự, thêm Đ.

Hai điểm bắt buộc phải làm đúng, nếu sai thì số đo vô nghĩa:
  1. Mỗi checkpoint mang charset riêng (khoá `charset`), phải giải mã bằng đúng
     bộ của nó. `CRNNRecognizer` trong pipeline cố định 37 ký tự nên không nạp
     được bản cũ; script này dùng recognizer riêng đọc charset từ checkpoint.
  2. Phải đi qua `read_plate(...)` với đúng `layout`: 15/17 biển nhóm này là biển
     2 hàng, đưa thẳng cả ảnh vào model mà không tách dòng thì kết quả là rác
     (thử lần đầu ra 1/17, trong khi đi đúng đường cho kết quả khác hẳn).

Biển seri MĐ là xe máy điện, TĐ là xe thí điểm, theo Thông tư 24/2023 và
79/2024/TT-BCA. Tập test hiện có 17 biển loại này, đa số là MĐ.

Chạy: .venv/Scripts/python.exe src/ml/eval_ocr_dplates.py
Xuất:  src/ml/experiments/ocr_dplates_before_after.csv
       docs/report/figures/plate_ocr_dplates_before_after.png
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src" / "ml" / "training"))
sys.path.insert(0, str(REPO_ROOT / "src" / "ml"))

import cv2  # noqa: E402
import matplotlib  # noqa: E402
import numpy as np  # noqa: E402
import torch  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from ocr_model import CRNN, IMG_HEIGHT, IMG_WIDTH  # noqa: E402
from pipeline.ocr import read_plate  # noqa: E402

TEST_CSV = REPO_ROOT / "data" / "processed" / "plate-ocr" / "test.csv"
WEIGHTS = REPO_ROOT / "src" / "ml" / "weights"
OUT_CSV = REPO_ROOT / "src" / "ml" / "experiments" / "ocr_dplates_before_after.csv"
OUT_FIG = REPO_ROOT / "docs" / "report" / "figures" / "plate_ocr_dplates_before_after.png"

MODELS = {
    "truoc": WEIGHTS / "plate-ocr-crnn-V3_seed42.pt",
    "sau": WEIGHTS / "plate-ocr-crnn.pt",
}


class CharsetRecognizer:
    """Cùng interface `recognize(image_bgr) -> (text, conf)` với `CRNNRecognizer`
    để dùng chung được `read_plate`, nhưng lấy charset từ chính checkpoint thay
    vì hằng số của module. Cần thiết vì bản trước và sau khác số lớp đầu ra."""

    def __init__(self, ckpt_path: Path) -> None:
        ckpt = torch.load(ckpt_path, map_location="cpu", weights_only=False)
        self.charset: str = ckpt["charset"]
        self._model = CRNN(num_classes=len(self.charset) + 1)
        self._model.load_state_dict(ckpt["model_state"])
        self._model.eval()

    def recognize(self, image_bgr: np.ndarray) -> tuple[str, float]:
        img = cv2.resize(image_bgr, (IMG_WIDTH, IMG_HEIGHT), interpolation=cv2.INTER_LINEAR)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0
        with torch.no_grad():
            logits = self._model(torch.from_numpy(gray[None, None]))[0].numpy()

        exp = np.exp(logits - logits.max(axis=1, keepdims=True))
        probs = exp / exp.sum(axis=1, keepdims=True)
        conf = float(probs.max(axis=1).mean())

        ids, out, prev = logits.argmax(axis=1).tolist(), [], -1
        for i in ids:
            if i != prev and i != 0:
                out.append(self.charset[i - 1])
            prev = i
        return "".join(out), conf


def main() -> None:
    rows = [r for r in csv.DictReader(open(TEST_CSV, encoding="utf-8")) if "Đ" in r["label_clean"]]
    n_2row = sum(r["layout"] == "bien_2hang" for r in rows)
    print(f"Tìm thấy {len(rows)} biển có ký tự Đ ({n_2row} biển 2 hàng, {len(rows) - n_2row} biển 1 hàng)")

    recs = {}
    for name, path in MODELS.items():
        recs[name] = CharsetRecognizer(path)
        cs = recs[name].charset
        print(f"  model {name:6s}: {path.name}  ({len(cs)} ký tự, có Đ: {'Đ' in cs})")

    results = []
    for r in rows:
        img_path = REPO_ROOT / r["image_path"].replace("\\", "/")
        img = cv2.imread(str(img_path))
        if img is None:
            print(f"  [bỏ qua] không đọc được ảnh: {img_path}")
            continue
        truth = r["label_clean"]
        preds = {n: read_plate(img, rec, layout=r["layout"]).text_normalized for n, rec in recs.items()}
        results.append({
            "anh": Path(r["image_path"]).name,
            "layout": r["layout"],
            "nhan_dung": truth,
            "truoc": preds["truoc"],
            "sau": preds["sau"],
            "truoc_dung_ca_bien": preds["truoc"] == truth,
            "sau_dung_ca_bien": preds["sau"] == truth,
            # Tách riêng khỏi "đúng cả biển": model có thể đọc đúng Đ nhưng sai
            # một chữ số khác, vẫn là tiến bộ thật so với bản cũ vốn không có
            # lớp ký tự này nên không bao giờ đọc ra được.
            "truoc_co_D": "Đ" in preds["truoc"],
            "sau_co_D": "Đ" in preds["sau"],
            "_img": img,
        })

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    fields = [k for k in results[0] if not k.startswith("_")]
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for r in results:
            w.writerow({k: r[k] for k in fields})

    n = len(results)
    tb, sb = sum(r["truoc_dung_ca_bien"] for r in results), sum(r["sau_dung_ca_bien"] for r in results)
    td, sd = sum(r["truoc_co_D"] for r in results), sum(r["sau_co_D"] for r in results)
    print(f"\n{'':26s} {'TRƯỚC':>8s} {'SAU':>8s}")
    print(f"{'Đúng cả biển':26s} {f'{tb}/{n}':>8s} {f'{sb}/{n}':>8s}")
    print(f"{'Đọc ra được ký tự Đ':26s} {f'{td}/{n}':>8s} {f'{sd}/{n}':>8s}")
    print(f"\nĐã ghi {OUT_CSV.relative_to(REPO_ROOT)}")

    cols = 3
    rows_n = (n + cols - 1) // cols
    fig, axes = plt.subplots(rows_n, cols, figsize=(cols * 4.4, rows_n * 2.1))
    for ax, r in zip(axes.ravel(), results):
        ax.imshow(cv2.cvtColor(r["_img"], cv2.COLOR_BGR2RGB))
        ok_after = r["sau_dung_ca_bien"]
        ax.set_title(
            f"thật: {r['nhan_dung']}\n"
            f"trước: {r['truoc'] or '(rỗng)'} {'✓' if r['truoc_dung_ca_bien'] else '✗'}   "
            f"sau: {r['sau'] or '(rỗng)'} {'✓' if ok_after else '✗'}",
            fontsize=8,
            color="#1b7f4b" if ok_after and not r["truoc_dung_ca_bien"] else "#333333",
        )
        ax.axis("off")
    for ax in axes.ravel()[n:]:
        ax.axis("off")
    fig.suptitle(
        f"Biển seri MĐ/TĐ: model trước ({len(recs['truoc'].charset)} ký tự) "
        f"so với sau ({len(recs['sau'].charset)} ký tự, thêm Đ)",
        fontsize=12,
    )
    fig.tight_layout()
    OUT_FIG.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_FIG, dpi=130, bbox_inches="tight")
    print(f"Đã ghi {OUT_FIG.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
