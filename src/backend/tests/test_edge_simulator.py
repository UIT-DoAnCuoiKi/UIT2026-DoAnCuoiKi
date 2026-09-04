import json

from scripts.simulate_edge import load_payload


def test_load_payload_reads_sidecar(tmp_path):
    img = tmp_path / "car.jpg"
    img.write_bytes(b"x")
    (tmp_path / "car.json").write_text(json.dumps({"vehicle_type": "car", "plates": []}))
    assert load_payload(img)["vehicle_type"] == "car"


def test_load_payload_default_when_no_sidecar(tmp_path):
    img = tmp_path / "moto.jpg"
    img.write_bytes(b"x")
    p = load_payload(img)
    assert p["vehicle_type"] is None
    assert p["plates"] == []
