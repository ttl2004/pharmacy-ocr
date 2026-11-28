"""Các loại tài liệu (profile). Mỗi profile = danh sách cột + prompt LLM.

Hiện chỉ còn profile thuốc (drug). Thêm loại tài liệu mới:
    1. Tạo file mới trong thư mục này (copy drug.py), sửa COLUMNS và SYSTEM_PROMPT.
    2. Thêm vào dict PROFILES bên dưới.
"""
from . import drug
from .base import KIND_LIST, KIND_NUTRITION, KIND_TEXT, Field, Profile

PROFILES: dict[str, Profile] = {
    drug.PROFILE.key: drug.PROFILE,
}

# Profile duy nhất của service và 16 key theo thứ tự cột
DRUG_PROFILE: Profile = drug.PROFILE
FIELD_KEYS: tuple[str, ...] = tuple(DRUG_PROFILE.field_keys())


def get_profile(key: str) -> Profile:
    if key not in PROFILES:
        raise ValueError(f"Loại tài liệu không hợp lệ: {key}. Có: {', '.join(PROFILES)}")
    return PROFILES[key]


__all__ = ["DRUG_PROFILE", "FIELD_KEYS", "KIND_LIST", "KIND_NUTRITION", "KIND_TEXT", "PROFILES",
           "Field", "Profile", "get_profile"]
