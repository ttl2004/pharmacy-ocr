"""Body request của API (pydantic v2)."""
from typing import Literal

from pydantic import BaseModel, Field


class RerunBody(BaseModel):
    """Chạy lại extraction: full (OCR + LLM) hoặc llm_only (dùng lại text OCR cũ)."""
    mode: Literal["full", "llm_only"]
    prompt_id: int | None = None


class FeedbackBody(BaseModel):
    """Đánh giá và bản duyệt cuối của người dùng."""
    rating: int = Field(ge=1, le=5)
    final_fields: dict[str, str]


class PromptCreateBody(BaseModel):
    """Tạo version prompt mới."""
    name: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1)
    note: str = ""


class ParseBody(BaseModel):
    """Parse thử các trường dạng text."""
    fields: dict[str, str]
