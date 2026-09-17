from app.models import ParkingSession, PlateReading
from app.security import crypto, plate


def _reading(db, *, direction="in", plate_text="51F-123.45", cid=None):
    r = PlateReading(
        capture_id=cid or f"cap-{plate_text}-{direction}",
        direction=direction,
        plate_text_ciphertext=crypto.encrypt_text(plate_text),
        plate_hash=plate.plate_hash(plate_text),
        plate_valid=True,
        vehicle_type="car",
        review_state="confident",
    )
    db.add(r)
    db.commit()
    db.refresh(r)
    return r


def test_ma_phieu_gom_bien_so_va_phan_duoi(client, db_session, staff_headers):
    r = client.post("/sessions/entry", json={"reading_id": _reading(db_session).id}, headers=staff_headers)
    code = r.json()["code"]
    bien, _, duoi = code.partition("-")
    assert bien == "51F12345"          # biển số bỏ dấu chấm và gạch nối
    assert len(duoi) == 5 and duoi == duoi.upper()


def test_tra_phien_theo_ma_phieu(client, db_session, staff_headers):
    entry = client.post("/sessions/entry", json={"reading_id": _reading(db_session).id}, headers=staff_headers).json()
    got = client.get(f"/sessions/by-code/{entry['code']}", headers=staff_headers)
    assert got.status_code == 200
    assert got.json()["id"] == entry["id"]


def test_ma_khong_co_trong_bai_tra_404(client, db_session, staff_headers):
    assert client.get("/sessions/by-code/51F12345-ABCDE", headers=staff_headers).status_code == 404


def test_go_moi_phan_duoi_van_tra_dung_phien(client, db_session, staff_headers):
    entry = client.post("/sessions/entry", json={"reading_id": _reading(db_session).id}, headers=staff_headers).json()
    duoi = entry["code"].rsplit("-", 1)[1]
    assert client.get(f"/sessions/by-code/{duoi}", headers=staff_headers).json()["id"] == entry["id"]


def test_ma_qua_ngan_tra_400(client, db_session, staff_headers):
    assert client.get("/sessions/by-code/AB12", headers=staff_headers).status_code == 400
    assert client.get("/sessions/by-code/51F12345-AB1", headers=staff_headers).status_code == 400


def test_xe_da_ra_thi_khong_tra_theo_ma(client, db_session, staff_headers):
    entry = client.post("/sessions/entry", json={"reading_id": _reading(db_session).id}, headers=staff_headers).json()
    session = db_session.get(ParkingSession, entry["id"])
    session.status = "completed"
    db_session.commit()
    assert client.get(f"/sessions/by-code/{entry['code']}", headers=staff_headers).status_code == 404
