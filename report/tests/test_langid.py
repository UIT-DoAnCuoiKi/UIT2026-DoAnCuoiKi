import re
from pathlib import Path

REFS = Path(__file__).resolve().parents[1] / "refs.bib"


def entries():
    text = REFS.read_text(encoding="utf-8")
    # Each entry begins with @type{key,
    return re.findall(r"@\w+\{([^,]+),(.*?)(?=\n@|\Z)", text, re.DOTALL)


def test_every_entry_has_valid_langid():
    missing = []
    for key, body in entries():
        m = re.search(r"langid\s*=\s*\{(vietnamese|english)\}", body)
        if not m:
            missing.append(key)
    assert not missing, f"entries without valid langid: {missing}"
