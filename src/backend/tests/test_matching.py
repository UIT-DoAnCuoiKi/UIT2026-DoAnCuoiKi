from app.services.matching import Candidate, edit_distance, find_match


def test_edit_distance_basic():
    assert edit_distance("51F12345", "51F12345") == 0
    assert edit_distance("51F12345", "51F12346") == 1
    assert edit_distance("51F12345", "51F12300") == 2


def _c(sid, norm, group="o_to_con", hashv=None):
    return Candidate(session_id=sid, plate_hash=hashv or f"h{sid}", plate_norm=norm, vehicle_group=group)


def test_exact_unique():
    cands = [_c(1, "51F12345", hashv="H")]
    r = find_match("H", "51F12345", "o_to_con", cands)
    assert r.kind == "exact" and r.session_id == 1 and r.match_flag == "exact"


def test_exact_multiple_suggests():
    cands = [_c(1, "51F12345", hashv="H"), _c(2, "51F12345", hashv="H")]
    r = find_match("H", "51F12345", "o_to_con", cands)
    assert r.kind == "suggest" and set(r.candidate_ids) == {1, 2}


def test_fuzzy_unique_k1_auto():
    cands = [_c(1, "51F12346")]  # cách biển đích 1 ký tự
    r = find_match("X", "51F12345", "o_to_con", cands)
    assert r.kind == "auto" and r.session_id == 1 and r.match_flag == "auto_corrected"


def test_fuzzy_k2_only_suggests():
    cands = [_c(1, "51F12300")]  # cách 2 ký tự
    r = find_match("X", "51F12345", "o_to_con", cands)
    assert r.kind == "suggest" and r.candidate_ids == [1]


def test_two_close_candidates_suggest():
    cands = [_c(1, "51F12346"), _c(2, "51F12344")]  # cả hai cách 1
    r = find_match("X", "51F12345", "o_to_con", cands)
    assert r.kind == "suggest" and set(r.candidate_ids) == {1, 2}


def test_group_filter_excludes():
    cands = [_c(1, "51F12346", group="xe_may")]
    r = find_match("X", "51F12345", "o_to_con", cands)
    assert r.kind == "none"


def test_no_candidate_within_two():
    cands = [_c(1, "99Z99999")]
    r = find_match("X", "51F12345", "o_to_con", cands)
    assert r.kind == "none"
