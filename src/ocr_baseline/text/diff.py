"""So sánh bản đề xuất của LLM với bản người dùng đã duyệt."""
from difflib import SequenceMatcher

from ..constants import EDIT_CLEARED, EDIT_FILLED, EDIT_MAJOR, EDIT_MINOR, EDIT_UNCHANGED
from ..profiles import FIELD_KEYS

_STATUSES = (EDIT_UNCHANGED, EDIT_MINOR, EDIT_MAJOR, EDIT_FILLED, EDIT_CLEARED)


def normalize_ws(text: str) -> str:
    """Gộp mọi khoảng trắng liên tiếp thành một dấu cách và bỏ khoảng trắng hai đầu."""
    return " ".join(text.split())


def classify(proposed: str, final: str, minor_threshold: float) -> tuple[str, float]:
    """Phân loại mức sửa của một trường, trả (status, độ tương đồng)."""
    a, b = normalize_ws(proposed), normalize_ws(final)
    if a == b:
        return EDIT_UNCHANGED, 1.0
    if not a:
        return EDIT_FILLED, 0.0
    if not b:
        return EDIT_CLEARED, 0.0
    r = round(SequenceMatcher(None, a, b, autojunk=False).ratio(), 3)
    return (EDIT_MINOR if r >= minor_threshold else EDIT_MAJOR), r


def compare_fields(proposed: dict[str, str], final: dict[str, str], minor_threshold: float) -> dict:
    """So sánh theo FIELD_KEYS, trả {"fields": {key: {status, similarity}}, "summary": {status: số lượng}}."""
    fields: dict[str, dict] = {}
    summary = {s: 0 for s in _STATUSES}
    for key in FIELD_KEYS:
        status, similarity = classify(proposed.get(key, ""), final.get(key, ""), minor_threshold)
        fields[key] = {"status": status, "similarity": similarity}
        summary[status] += 1
    return {"fields": fields, "summary": summary}
