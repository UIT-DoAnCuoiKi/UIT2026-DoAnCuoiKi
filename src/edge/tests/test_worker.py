"""Test edge worker tách khỏi phần cứng: FakeTrigger/FakeCamera/FakePipeline +
httpx MockTransport. Không cần camera, GPIO hay model thật."""
import json
import sys

import httpx
import numpy as np
import pytest

from worker import CapturePoster, GpioTrigger, StopWorker, run_worker


class FakeTrigger:
    """Bắn `times` lần rồi dừng worker (giống một xe mỗi lần, rồi tắt)."""

    def __init__(self, times: int = 1) -> None:
        self._left = times

    def wait(self) -> None:
        if self._left <= 0:
            raise StopWorker
        self._left -= 1


class FakeCamera:
    def __init__(self, frame, ok: bool = True) -> None:
        self._frame = frame
        self._ok = ok
        self.released = False

    def read(self):
        return self._ok, self._frame

    def release(self) -> None:
        self.released = True


class FakePipeline:
    def __init__(self, result: dict) -> None:
        self._result = result

    def run(self, frame) -> dict:
        return self._result


def _frame():
    return np.zeros((8, 8, 3), dtype=np.uint8)


def _result_with_plate():
    return {
        "vehicle_type": "car", "vehicle_box": None,
        "vehicle_style": None, "vehicle_style_conf": None,
        "plates": [{
            "bbox": [0, 0, 5, 5], "layout": "1", "det_conf": 0.7,
            "plate_text": "51F999", "plate_valid": True, "ocr_conf": 0.85,
            "color": "white", "color_conf": 0.9,
        }],
    }


def _empty_result():
    return {
        "vehicle_type": None, "vehicle_box": None,
        "vehicle_style": None, "vehicle_style_conf": None, "plates": [],
    }


def test_worker_posts_inferred_payload():
    result = _result_with_plate()
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["request"] = request
        captured["body"] = request.content.decode("utf-8", "replace")
        return httpx.Response(200, json={"ok": True})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    poster = CapturePoster(
        client, backend="http://backend:8000", edge_key="edge-dev-key",
        direction="in", lane="L1", sleep=lambda _s: None,
    )

    run_worker(FakeTrigger(1), FakeCamera(_frame()), FakePipeline(result), poster)

    req = captured["request"]
    assert req.method == "POST"
    assert req.url.path == "/captures"
    assert req.headers["X-Edge-Key"] == "edge-dev-key"

    body = captured["body"]
    assert 'name="capture_id"' in body
    assert 'name="direction"' in body
    assert 'name="lane"' in body
    assert 'name="image"' in body
    # payload là json của dict suy luận, khớp nguyên văn
    assert json.dumps(result) in body


def test_worker_retries_then_drops():
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        raise httpx.ConnectError("mạng hỏng", request=request)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    poster = CapturePoster(
        client, backend="http://backend:8000", edge_key="k",
        direction="in", retries=3, backoff=0.0, sleep=lambda _s: None,
    )

    # Không được sập worker khi POST liên tục lỗi.
    run_worker(FakeTrigger(1), FakeCamera(_frame()), FakePipeline(_empty_result()), poster)

    assert calls["n"] == 3


def test_gpio_trigger_missing_dep(monkeypatch):
    # ép `import gpiozero` ném ImportError dù máy dev có/không cài.
    monkeypatch.setitem(sys.modules, "gpiozero", None)
    with pytest.raises(RuntimeError) as exc:
        GpioTrigger(17)
    msg = str(exc.value).lower()
    assert "gpiozero" in msg or "pi" in msg
