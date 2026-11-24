"""Thống kê đánh giá và độ lệch bản duyệt. Hàm thuần: nhận danh sách dòng, trả dict."""
from collections import defaultdict

from .constants import EDIT_CLEARED, EDIT_FILLED, EDIT_MAJOR, EDIT_MINOR, EDIT_UNCHANGED
from .profiles import FIELD_KEYS
from .storage.models import StatsRow

_STATUSES = (EDIT_UNCHANGED, EDIT_MINOR, EDIT_MAJOR, EDIT_FILLED, EDIT_CLEARED)
_UNKNOWN = "unknown"


def _key_of(row: StatsRow, group_by: str) -> str:
    """Key nhóm cho 3 cách nhóm theo extraction; giá trị None thành "unknown"."""
    value = {"prompt": row.prompt_id, "engine": row.engine, "model": row.llm_model}[group_by]
    return _UNKNOWN if value is None else str(value)


def _field_statuses(row: StatsRow) -> dict[str, str]:
    """Status từng trường của một extraction (lấy từ diff["fields"])."""
    return {k: v.get("status", EDIT_UNCHANGED) for k, v in row.diff.get("fields", {}).items()}


def _round_avg(values: list, digits: int) -> float:
    return round(sum(values) / len(values), digits) if values else 0.0


def _build_group(key: str, ratings: list[int], units: list[tuple[str, str]],
                 field_keys, count: int, totals: dict[str, int]) -> dict:
    """Dựng một nhóm. units = [(field, status)] của mọi đơn vị thuộc nhóm."""
    status_counts = {s: 0 for s in _STATUSES}
    edited: dict[str, int] = defaultdict(int)
    for field, status in units:
        if status in status_counts:
            status_counts[status] += 1
        if status != EDIT_UNCHANGED:
            edited[field] += 1
    edit_rate = {f: round(edited[f] / totals[f], 3) for f in field_keys if totals.get(f)}
    return {"key": key, "count": count, "avg_rating": _round_avg(ratings, 2),
            "edit_rate": edit_rate, "status_counts": status_counts}


def _group_by_extraction(rows: list[StatsRow], group_by: str) -> list[dict]:
    """Mỗi extraction là một đơn vị."""
    buckets: dict[str, list[StatsRow]] = defaultdict(list)
    for r in rows:
        buckets[_key_of(r, group_by)].append(r)
    groups = []
    for key, items in buckets.items():
        units = [(f, s) for r in items for f, s in _field_statuses(r).items()]
        # Mẫu số edit_rate là số extraction; trường vắng trong diff coi như unchanged.
        totals = {f: len(items) for f in FIELD_KEYS}
        groups.append(_build_group(key, [r.rating for r in items], units, FIELD_KEYS, len(items), totals))
    return groups


def _group_by_source(rows: list[StatsRow]) -> list[dict]:
    """Mỗi trường là một đơn vị, nhóm theo nguồn (section/llm/none/unknown)."""
    units: dict[str, list[tuple[str, str]]] = defaultdict(list)
    ratings: dict[str, dict[int, int]] = defaultdict(dict)  # nguồn -> {chỉ số extraction: rating}
    totals: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for i, r in enumerate(rows):
        for field, status in _field_statuses(r).items():
            src = r.sources.get(field) or _UNKNOWN
            units[src].append((field, status))
            ratings[src][i] = r.rating
            totals[src][field] += 1
    groups = []
    for src, items in units.items():
        seen = [f for f in FIELD_KEYS if totals[src].get(f)]
        seen += sorted(f for f in totals[src] if f not in FIELD_KEYS)
        groups.append(_build_group(src, list(ratings[src].values()), items, seen, len(items), totals[src]))
    return groups


def _rating_vs_edits(rows: list[StatsRow]) -> list[dict]:
    """Số trường bị sửa trung bình theo từng mức rating (giảm dần)."""
    by_rating: dict[int, list[int]] = defaultdict(list)
    for r in rows:
        by_rating[r.rating].append(sum(1 for s in _field_statuses(r).values() if s != EDIT_UNCHANGED))
    return [{"rating": rt, "avg_edited_fields": _round_avg(by_rating[rt], 2)}
            for rt in sorted(by_rating, reverse=True)]


def compute_stats(rows: list[StatsRow], group_by: str) -> dict:
    """Trả {"group_by", "groups", "rating_vs_edits"}; groups sắp xếp theo key."""
    if not rows:
        return {"group_by": group_by, "groups": [], "rating_vs_edits": []}
    groups = _group_by_source(rows) if group_by == "source" else _group_by_extraction(rows, group_by)
    groups.sort(key=lambda g: g["key"])
    return {"group_by": group_by, "groups": groups, "rating_vs_edits": _rating_vs_edits(rows)}
