"""Xuất đặc tả OpenAPI ra file, không cần chạy server.

Import app rồi gọi app.openapi(), ghi JSON. Dùng để sinh client Orval ở
frontend mà không phải dựng backend (hợp cho CI và máy chưa mở service).

    python scripts/export_openapi.py [output_path]

Mặc định ghi ../frontend/openapi.json (đúng input trong orval.config.ts).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Cho phép chạy trực tiếp từ thư mục backend (import app.*).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.main import app  # noqa: E402

DEFAULT_OUT = Path(__file__).resolve().parent.parent.parent / "frontend" / "openapi.json"


def main() -> None:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_OUT
    out.parent.mkdir(parents=True, exist_ok=True)
    spec = app.openapi()
    out.write_text(json.dumps(spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Đã ghi OpenAPI ({len(spec['paths'])} path) vào {out}")


if __name__ == "__main__":
    main()
