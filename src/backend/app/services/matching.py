from dataclasses import dataclass, field


def edit_distance(a: str, b: str) -> int:
    if a == b:
        return 0
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        cur = [i]
        for j, cb in enumerate(b, start=1):
            cost = 0 if ca == cb else 1
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost))
        prev = cur
    return prev[-1]


@dataclass(frozen=True)
class Candidate:
    session_id: int
    plate_hash: str
    plate_norm: str
    vehicle_group: str


@dataclass
class MatchResult:
    kind: str  # exact | auto | suggest | none
    session_id: int | None = None
    match_flag: str | None = None
    candidate_ids: list[int] = field(default_factory=list)


def find_match(target_hash: str, target_norm: str, group: str, candidates: list[Candidate]) -> MatchResult:
    exact = [c for c in candidates if target_hash and c.plate_hash == target_hash]
    if len(exact) == 1:
        return MatchResult("exact", session_id=exact[0].session_id, match_flag="exact")
    if len(exact) > 1:
        return MatchResult("suggest", candidate_ids=[c.session_id for c in exact])

    scored = [(c, edit_distance(target_norm, c.plate_norm)) for c in candidates if c.vehicle_group == group]
    scored = [(c, d) for c, d in scored if d <= 2]
    if not scored:
        return MatchResult("none")
    if len(scored) == 1 and scored[0][1] <= 1:
        return MatchResult("auto", session_id=scored[0][0].session_id, match_flag="auto_corrected")
    scored.sort(key=lambda cd: cd[1])
    return MatchResult("suggest", candidate_ids=[c.session_id for c, _ in scored])
