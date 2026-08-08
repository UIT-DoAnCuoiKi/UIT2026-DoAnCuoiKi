from __future__ import annotations
from statistics import median


def infer_layout_map(objects_by_class: dict[int, list[float]]) -> dict[int, str]:
    med = {cid: median(ars) for cid, ars in objects_by_class.items()}
    wide_id = max(med, key=med.get)   # highest aspect ratio == 1-row (long plate)
    return {cid: ("bien_1hang" if cid == wide_id else "bien_2hang") for cid in med}


def verify_class_map(inferred: dict[int, str], yaml_names: dict[int, str] | None) -> dict[int, str]:
    if yaml_names is not None:
        for cid, name in inferred.items():
            yn = str(yaml_names.get(cid, "")).lower()
            is_1 = any(k in yn for k in ("1hang", "dai", "long", "lpd", "bsd"))
            is_2 = any(k in yn for k in ("2hang", "vuong", "square", "lpv", "bsv"))
            if is_1 and name != "bien_1hang":
                raise ValueError(f"class {cid}: yaml '{yn}' vs inferred '{name}'")
            if is_2 and name != "bien_2hang":
                raise ValueError(f"class {cid}: yaml '{yn}' vs inferred '{name}'")
    return inferred
