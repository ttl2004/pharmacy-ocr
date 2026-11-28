"""Prompt cho LLM, quản lý theo phiên bản.

- Prompt KHÔNG bị sửa đè: mỗi lần sửa tạo phiên bản mới (cùng tên, version + 1). Extraction lưu
  prompt_id nên luôn biết chính xác nội dung prompt đã tạo ra kết quả.
- Prompt gốc (is_builtin) lấy từ code trong profiles/, không sửa được qua API.
"""
from dataclasses import dataclass

from .profiles import DRUG_PROFILE


@dataclass(frozen=True)
class Prompt:
    id: int
    name: str
    version: int
    content: str
    note: str = ""
    is_builtin: bool = False
    is_active: bool = False
    created_at: str = ""

    @property
    def label(self) -> str:
        """Tên hiển thị, vd "Thuốc - prompt mặc định (gốc) · v2"."""
        return f"{self.name} · v{self.version}"


def builtin_prompt() -> tuple[str, str]:
    """Prompt gốc: (tên, nội dung)."""
    return DRUG_PROFILE.default_prompt_name, DRUG_PROFILE.system_prompt


def missing_field_keys(content: str) -> list[str]:
    """Các cột không được nhắc tới trong prompt -> LLM có thể không trả về cột đó."""
    return [key for key in DRUG_PROFILE.field_keys() if key not in content]


def prompt_to_json(p: Prompt) -> dict:
    return {
        "id": p.id,
        "name": p.name,
        "version": p.version,
        "content": p.content,
        "note": p.note,
        "is_active": p.is_active,
        "is_builtin": p.is_builtin,
        "created_at": p.created_at,
    }
