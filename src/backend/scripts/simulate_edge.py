import argparse
import json
import time
import uuid
from pathlib import Path
from typing import Callable, TypeVar

import httpx

T = TypeVar("T")


def _retry_eintr(fn: Callable[[], T], attempts: int = 10, delay: float = 0.2) -> T:
    """Retry khi InterruptedError (EINTR). Mount chia sẻ của VM (libkrun/virtiofs)
    có thể trả EINTR cho scandir/read; PEP 475 không phải lúc nào cũng tự thử lại."""
    last: BaseException | None = None
    for _ in range(attempts):
        try:
            return fn()
        except InterruptedError as exc:
            last = exc
            time.sleep(delay)
    assert last is not None
    raise last


def load_payload(img_path: Path) -> dict:
    sidecar = img_path.with_suffix(".json")
    if sidecar.exists():
        return json.loads(sidecar.read_text())
    return {"vehicle_type": None, "vehicle_style": None, "vehicle_style_conf": None, "plates": []}


def _list_jpgs(images_dir: str) -> list[Path]:
    return _retry_eintr(lambda: sorted(
        p for p in Path(images_dir).iterdir() if p.suffix.lower() == ".jpg"
    ))


def post_folder(images_dir: str, backend: str, direction: str, lane: str, edge_key: str) -> None:
    for img_path in _list_jpgs(images_dir):
        payload = load_payload(img_path)
        raw = _retry_eintr(img_path.read_bytes)
        files = {"image": (img_path.name, raw, "image/jpeg")}
        data = {
            "capture_id": str(uuid.uuid4()),
            "direction": direction,
            "lane": lane,
            "payload": json.dumps(payload),
        }
        resp = httpx.post(
            f"{backend}/captures", data=data, files=files,
            headers={"X-Edge-Key": edge_key}, timeout=30.0,
        )
        print(img_path.name, resp.status_code, resp.text[:200])


def main() -> None:
    ap = argparse.ArgumentParser(description="Giả lập edge worker: đọc ảnh thư mục và POST /captures")
    ap.add_argument("--images", required=True)
    ap.add_argument("--backend", default="http://localhost:8000")
    ap.add_argument("--direction", default="in", choices=["in", "out"])
    ap.add_argument("--lane", default="lane1")
    ap.add_argument("--edge-key", default="edge-dev-key")
    args = ap.parse_args()
    post_folder(args.images, args.backend, args.direction, args.lane, args.edge_key)


if __name__ == "__main__":
    main()
