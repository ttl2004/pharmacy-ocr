"""Endpoint thống kê và parse thử các trường có cấu trúc."""
from typing import Literal

from fastapi import APIRouter, Request

from ..constants import STRUCTURED_FIELDS
from ..stats import compute_stats
from ..text import parse_structured
from .errors import api_error
from .schemas import ParseBody

router = APIRouter()


@router.get("/stats")
def get_stats(request: Request, group_by: Literal["prompt", "engine", "model", "source"] = "prompt"):
    """Thống kê đánh giá và mức độ chỉnh sửa theo cách nhóm được chọn."""
    return compute_stats(request.app.state.feedback.list_for_stats(), group_by)


@router.post("/parse")
def parse_fields(body: ParseBody):
    """Parse thử hoạt chất/quy cách/hạn dùng từ text."""
    extra = sorted(set(body.fields) - set(STRUCTURED_FIELDS))
    if extra:
        raise api_error("invalid_request", f"Key không hợp lệ: {', '.join(extra)}")
    return {"structured": parse_structured(body.fields)}
