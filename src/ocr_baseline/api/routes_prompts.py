"""Endpoint quản lý prompt: liệt kê, tạo version mới, kích hoạt."""
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from ..prompts import missing_field_keys, prompt_to_json
from .errors import api_error
from .schemas import PromptCreateBody

router = APIRouter()


@router.get("/prompts")
def list_prompts(request: Request):
    """Danh sách mọi version prompt."""
    return [prompt_to_json(p) for p in request.app.state.prompts.list()]


@router.post("/prompts")
def create_prompt(body: PromptCreateBody, request: Request):
    """Tạo version prompt mới; từ chối khi prompt không nhắc tới đủ các cột."""
    missing = missing_field_keys(body.content)
    if missing:
        raise api_error("invalid_request", f"Prompt thiếu các key: {', '.join(missing)}")
    prompt = request.app.state.prompts.create(body.name, body.content, body.note)
    return JSONResponse(status_code=201, content=prompt_to_json(prompt))


@router.post("/prompts/{prompt_id}/activate")
def activate_prompt(prompt_id: int, request: Request):
    """Đặt prompt làm bản đang dùng."""
    prompt = request.app.state.prompts.activate(prompt_id)
    if prompt is None:
        raise api_error("not_found", "Không có prompt này")
    return prompt_to_json(prompt)
