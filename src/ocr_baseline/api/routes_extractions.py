"""Endpoint tạo extraction."""
from uuid import uuid4

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import JSONResponse

from ..constants import MODE_FULL, STATUS_QUEUED
from ..images import (UploadRejected, check_count, check_image, delete_images,
                      optimize_to_webp, save_images)
from .errors import api_error

router = APIRouter()


@router.post("/extractions")
def create_extraction(request: Request,
                      images: list[UploadFile] = File(..., alias="images[]"),
                      prompt_id: int | None = Form(None)):
    """Nhận ảnh, tối ưu thành WebP, lưu và xếp job vào hàng đợi (202)."""
    state = request.app.state
    settings = state.settings
    try:
        check_count(len(images), settings.max_images)
        raw: list[bytes] = []
        for i, f in enumerate(images):
            # Đọc tối đa max+1 byte là đủ để phát hiện ảnh quá lớn.
            data = f.file.read(settings.max_image_bytes + 1)
            check_image(data, i, settings.max_image_bytes)
            raw.append(data)

        if prompt_id is not None:
            prompt = state.prompts.get(prompt_id)
            if prompt is None:
                raise api_error("not_found", f"Không tìm thấy prompt {prompt_id}")
        else:
            prompt = state.prompts.get_active()

        optimized = [optimize_to_webp(d, settings.image_max_side, settings.image_quality) for d in raw]
    except UploadRejected as e:
        raise api_error(e.code, e.message) from e

    extraction_id = uuid4().hex
    try:
        # save_images nằm trong try để lỗi ghi giữa chừng không để lại file mồ côi.
        records = save_images(settings.storage_dir, extraction_id, optimized)
        state.extractions.create(extraction_id, prompt.id, MODE_FULL, records)
    except Exception:
        delete_images(settings.storage_dir, extraction_id)
        raise
    return JSONResponse(status_code=202, content={"id": extraction_id, "status": STATUS_QUEUED})
