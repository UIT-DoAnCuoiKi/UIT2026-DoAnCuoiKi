import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import Base
import app.models as m
from app.security import crypto, plate


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def test_store_encrypted_plate_then_match_by_hash():
    db = _session()
    raw = "51F-123.45"
    db.add(m.PlateReading(
        capture_id="cap-1",
        direction="in",
        plate_text_ciphertext=crypto.encrypt_text(raw),
        plate_hash=plate.plate_hash(raw),
        review_state="confident",
    ))
    db.commit()

    # biển đọc lại viết khác cách nhưng cùng biển, phải khớp qua hash
    q = select(m.PlateReading).where(m.PlateReading.plate_hash == plate.plate_hash("51f 123 45"))
    found = db.scalars(q).one()
    assert crypto.decrypt_text(found.plate_text_ciphertext) == raw


def test_capture_id_uniqueness_enforced():
    db = _session()
    db.add(m.PlateReading(capture_id="dup", direction="in", review_state="manual"))
    db.commit()
    db.add(m.PlateReading(capture_id="dup", direction="out", review_state="manual"))
    with pytest.raises(IntegrityError):
        db.commit()
