"""E2E API tests: chạy vào backend HTTP thật (không phải TestClient in-process).

Chạy stack trước (podman compose up db backend retention), rồi:
    pytest tests_e2e            # mặc định BASE_URL=http://localhost:8000
Biến môi trường: BASE_URL, EDGE_API_KEY, ADMIN_USERNAME, ADMIN_PASSWORD.
Nếu backend không chạy, cả module tự skip.
"""
import os

import httpx
import pytest

BASE = os.environ.get("BASE_URL", "http://localhost:8000")
EDGE_KEY = os.environ.get("EDGE_API_KEY", "edge-dev-key")
ADMIN_USER = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASS = os.environ.get("ADMIN_PASSWORD", "admin12345")


@pytest.fixture(scope="session")
def api():
    client = httpx.Client(base_url=BASE, timeout=15.0)
    try:
        client.get("/health").raise_for_status()
    except Exception:
        client.close()
        pytest.skip(f"backend không chạy ở {BASE}; đặt BASE_URL nếu khác")
    yield client
    client.close()


@pytest.fixture(scope="session")
def admin_h(api):
    r = api.post("/auth/login", json={"username": ADMIN_USER, "password": ADMIN_PASS})
    assert r.status_code == 200, f"login admin fail: {r.text}"
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture(scope="session")
def staff_h(api, admin_h):
    import uuid
    uname = "e2e_staff_" + uuid.uuid4().hex[:8]
    r = api.post("/users", json={"username": uname, "password": "pw", "role": "staff"}, headers=admin_h)
    assert r.status_code == 201, f"tạo staff fail: {r.text}"
    tok = api.post("/auth/login", json={"username": uname, "password": "pw"}).json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}
