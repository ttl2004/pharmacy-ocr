"""Tách văn bản OCR đã làm sạch thành các mục theo tiêu đề (đã bỏ dấu)."""

import re
import unicodedata
from difflib import SequenceMatcher

# Ngưỡng và giới hạn của khớp mờ
_FUZZY_THRESHOLD = 0.85
_FUZZY_MAX_LEN = 60

SECTION_HEADINGS: dict[str, tuple[str, ...]] = {
    "chi_dinh": ("chi dinh dieu tri", "chi dinh", "cong dung"),
    "chong_chi_dinh": ("chong chi dinh",),
    "lieu_dung_cach_dung": (
        "lieu luong va cach dung",
        "lieu dung va cach dung",
        "cach dung va lieu dung",
        "cach dung - lieu dung",
        "lieu dung - cach dung",
        "lieu dung",
        "cach dung",
    ),
    "tac_dung_khong_mong_muon": ("tac dung khong mong muon", "tac dung phu"),
    "than_trong": (
        "canh bao va than trong",
        "than trong khi dung thuoc",
        "than trong",
    ),
    "tuong_tac_thuoc": (
        "tuong tac, tuong ky cua thuoc",
        "tuong tac voi cac thuoc khac",
        "tuong tac thuoc",
    ),
    "phu_nu_co_thai_cho_con_bu": (
        "su dung thuoc cho phu nu co thai va cho con bu",
        "phu nu co thai va cho con bu",
        "thoi ky mang thai va cho con bu",
        "phu nu co thai",
    ),
    "qua_lieu": ("qua lieu va cach xu tri", "qua lieu"),
    "bao_quan": ("dieu kien bao quan", "bao quan"),
}

# Tiêu đề chỉ là ranh giới, không lấy nội dung
STOP_HEADINGS: tuple[str, ...] = (
    "thanh phan",
    "dang bao che",
    "quy cach dong goi",
    "duoc luc hoc",
    "duoc dong hoc",
    "dac tinh duoc luc hoc",
    "tac dong cua thuoc khi lai xe",
    "anh huong cua thuoc len kha nang lai xe",
    "han dung",
    "tieu chuan",
    "nha san xuat",
    "mo ta san pham",
)

# Tiền tố (số thứ tự, gạch đầu dòng...) bỏ trước khi so tiêu đề
_PREFIX_RE = re.compile(r"^[\s\d.\-•*+()]+")

# Danh sách (biến thể, key hoặc None cho stop), dài trước ngắn sau; tính một lần
_VARIANTS: list[tuple[str, str | None]] = sorted(
    [(v, k) for k, vs in SECTION_HEADINGS.items() for v in vs]
    + [(v, None) for v in STOP_HEADINGS],
    key=lambda item: len(item[0]),
    reverse=True,
)


def _fold_char(c: str) -> str:
    """Bỏ dấu một ký tự, luôn trả đúng một ký tự."""
    stripped = "".join(
        ch for ch in unicodedata.normalize("NFD", c) if unicodedata.category(ch) != "Mn"
    )
    out = stripped or c
    out = out.replace("đ", "d").replace("Đ", "D").lower()
    return out[0]


def fold(text: str) -> str:
    """Bỏ dấu, đổi đ thành d, viết thường; len(fold(s)) == len(s)."""
    return "".join(_fold_char(c) for c in text)


def _heading_case_ok(rest_line: str, variant_len: int) -> bool:
    """Phần tiêu đề của dòng gốc có chữ cái và toàn chữ hoa."""
    letters = [c for c in rest_line[:variant_len] if c.isalpha()]
    return bool(letters) and all(c.isupper() for c in letters)


def _match_exact(line: str, rest_line: str, core: str) -> tuple[str | None, int] | None:
    """Khớp chính xác; trả (key hoặc None cho stop, độ dài biến thể) hoặc None."""
    for variant, key in _VARIANTS:
        if not core.startswith(variant):
            continue
        tail = core[len(variant):].strip()
        if (
            tail == ""
            or tail.startswith(":")
            or line.isupper()
            or _heading_case_ok(rest_line, len(variant))
        ):
            return key, len(variant)
    return None


def _match_fuzzy(core: str) -> tuple[str | None] | None:
    """Khớp mờ cả dòng; trả (key hoặc None cho stop) của biến thể tốt nhất."""
    if not core or len(core) > _FUZZY_MAX_LEN:
        return None
    probe = core.rstrip(" :.")
    best_ratio, best_key = 0.0, None
    for variant, key in _VARIANTS:
        ratio = SequenceMatcher(None, probe, variant).ratio()
        if ratio > best_ratio:
            best_ratio, best_key = ratio, key
    if best_ratio >= _FUZZY_THRESHOLD:
        return (best_key,)
    return None


def split_sections(text: str, min_found: int) -> dict[str, str] | None:
    """Tách text thành các mục đích; None nếu tìm được ít hơn min_found mục."""
    chunks: dict[str, list[str]] = {}
    seen: set[str] = set()
    current: str | None = None

    for line in text.split("\n"):
        prefix = _PREFIX_RE.match(line)
        offset = prefix.end() if prefix else 0
        rest_line = line[offset:]
        core = fold(rest_line)

        key: str | None = None
        body = ""
        is_heading = False
        if core:
            exact = _match_exact(line, rest_line, core)
            if exact is not None:
                is_heading = True
                key = exact[0]
                body = rest_line[exact[1]:].lstrip(" :.-")
            else:
                fuzzy = _match_fuzzy(core)
                if fuzzy is not None:
                    is_heading = True
                    key = fuzzy[0]

        if is_heading and key is None:
            current = None  # stop heading: luôn là ranh giới
        elif is_heading and key not in seen:
            seen.add(key)
            current = key
            chunks[key] = [body] if body else []
        elif current is not None:
            chunks[current].append(line)  # nội dung (kể cả tiêu đề lặp lại)

    found = {k: "\n".join(v).strip() for k, v in chunks.items()}
    found = {k: v for k, v in found.items() if v}
    if len(found) < min_found:
        return None
    return found
