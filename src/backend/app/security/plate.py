import hashlib
import hmac
import re

from app.config import settings

_NON_ALNUM = re.compile(r"[^A-Z0-9]")


def normalize_plate(raw: str) -> str:
    return _NON_ALNUM.sub("", raw.upper())


def plate_hash(raw: str) -> str:
    norm = normalize_plate(raw)
    return hmac.new(settings.hmac_key.encode(), norm.encode(), hashlib.sha256).hexdigest()
