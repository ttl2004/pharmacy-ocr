"""Parser cấu trúc cho hoạt chất, quy cách đóng gói và hạn dùng."""

import re
from collections.abc import Mapping

from ..constants import STRUCTURED_FIELDS
from .sections import fold

# Tên, hàm lượng, đơn vị. Riêng "%" không đứng trước ranh giới từ nên tách khỏi nhóm \b.
_INGREDIENT_RE = re.compile(
    r"^(?P<ten>.+?)\s*[:\-]?\s*(?P<so>\d+(?:[.,]\d+)?)\s*"
    r"(?P<don_vi>(?:mg|mcg|µg|μg|g|ml|IU|UI)\b|%)",
    re.IGNORECASE,
)
_SPLIT_RE = re.compile(r"[;\n]")
_PACK_PAIR_RE = re.compile(r"(\d+)\s*([a-z]+)")
_SHELF_LIFE_RE = re.compile(r"(\d+)\s*(thang|nam|ngay)")

_UNIT_ALIASES = {"µg": "mcg", "μg": "mcg", "iu": "IU", "ui": "IU"}


def _to_number(raw: str) -> int | float:
    """Đổi ',' thành '.', trả int nếu là số nguyên."""
    value = float(raw.replace(",", "."))
    return int(value) if value.is_integer() else value


def parse_active_ingredients(text: str) -> list[dict] | None:
    """Tách theo ';' và xuống dòng; một mục không khớp thì cả trường là None."""
    if not text or not text.strip():
        return None
    items = [p.strip() for p in _SPLIT_RE.split(text) if p.strip()]
    if not items:
        return None
    result: list[dict] = []
    for item in items:
        m = _INGREDIENT_RE.match(item)
        if not m:
            return None
        unit = m.group("don_vi").lower()
        result.append(
            {
                "ten": m.group("ten").strip(" :-"),
                "ham_luong": _to_number(m.group("so")),
                "don_vi": _UNIT_ALIASES.get(unit, unit),
            }
        )
    return result


def parse_packaging(text: str) -> dict | None:
    """Chỉ xét đoạn đầu tiên; bao_bi là từ đứng trước chữ số đầu tiên."""
    if not text or not text.strip():
        return None
    segment = next((p for p in _SPLIT_RE.split(text) if p.strip()), "")
    folded = fold(segment)
    cap = [
        {"so_luong": int(n), "don_vi": u} for n, u in _PACK_PAIR_RE.findall(folded)
    ]
    if not cap:
        return None
    word = re.match(r"\s*([a-z]+)", folded)
    first_digit = re.search(r"\d", folded)
    bao_bi = None
    if word and (first_digit is None or word.end() <= first_digit.start()):
        bao_bi = word.group(1)
    return {"bao_bi": bao_bi, "cap": cap}


def parse_shelf_life(text: str) -> dict | None:
    """Lấy match đầu tiên dạng '<số> tháng|năm|ngày' trên văn bản đã fold."""
    if not text or not text.strip():
        return None
    m = _SHELF_LIFE_RE.search(fold(text))
    if not m:
        return None
    return {"so": int(m.group(1)), "don_vi": m.group(2)}


_PARSERS = {
    "hoat_chat_ham_luong": parse_active_ingredients,
    "quy_cach_dong_goi": parse_packaging,
    "han_dung": parse_shelf_life,
}


def parse_structured(fields: Mapping[str, str]) -> dict:
    """Luôn trả đủ các key STRUCTURED_FIELDS; thiếu hoặc rỗng thì None."""
    return {k: _PARSERS[k](fields.get(k) or "") for k in STRUCTURED_FIELDS}
