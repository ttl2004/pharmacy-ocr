"""Endpoint tạo extraction."""
from uuid import uuid4

from fastapi import APIRouter, File, Form, Request, Response, UploadFile
from fastapi.responses import FileResponse, JSONResponse

from ..constants import (IMAGE_CONTENT_TYPE, MODE_FULL, MODE_LLM_ONLY, STATUS_FAILED,
                         STATUS_QUEUED, STATUS_RUNNING, STATUS_SUCCEEDED)
from ..images import (UploadRejected, check_count, check_image, copy_images, delete_images,
                      image_file, optimize_to_webp, save_images)
from ..profiles import FIELD_KEYS
from ..text import compare_fields
from .dependencies import resolve_prompt
from .errors import api_error
from .schemas import FeedbackBody, RerunBody
from .serializers import extraction_to_json

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

        prompt = resolve_prompt(state, prompt_id)

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


@router.get("/extractions/{extraction_id}")
def get_extraction(extraction_id: str, request: Request):
    """Chi tiết extraction: trạng thái, ảnh, OCR, kết quả và bản duyệt."""
    state = request.app.state
    row = state.extractions.get(extraction_id)
    if row is None:
        raise api_error("not_found", f"Không tìm thấy extraction {extraction_id}")
    return extraction_to_json(row, state.extractions.list_images(extraction_id),
                              state.prompts.get(row.prompt_id), state.feedback.get(extraction_id))


@router.get("/extractions/{extraction_id}/images/{index}")
def get_extraction_image(extraction_id: str, index: int, request: Request):
    """Tải ảnh WebP đã tối ưu của extraction."""
    state = request.app.state
    record = next((r for r in state.extractions.list_images(extraction_id) if r.index == index), None)
    if record is None:
        raise api_error("not_found", f"Không tìm thấy ảnh {index} của extraction {extraction_id}")
    path = image_file(state.settings.storage_dir, record)
    if not path.is_file():
        raise api_error("not_found", f"Thiếu file ảnh {index} của extraction {extraction_id}")
    return FileResponse(path, media_type=IMAGE_CONTENT_TYPE)


@router.delete("/extractions/{extraction_id}")
def delete_extraction(extraction_id: str, request: Request):
    """Xoá extraction và ảnh (409 khi đang chạy)."""
    state = request.app.state
    row = state.extractions.get(extraction_id)
    if row is None:
        raise api_error("not_found", f"Không tìm thấy extraction {extraction_id}")
    if row.status == STATUS_RUNNING:
        raise api_error("invalid_state", "Extraction đang chạy, không thể xoá")
    state.extractions.delete(extraction_id)
    delete_images(state.settings.storage_dir, extraction_id)
    return Response(status_code=204)


@router.post("/extractions/{extraction_id}/rerun")
def rerun_extraction(extraction_id: str, body: RerunBody, request: Request):
    """Chạy lại extraction (full hoặc llm_only) thành bản mới, bản cũ bị thay thế (202)."""
    state = request.app.state
    storage_dir = state.settings.storage_dir
    old = state.extractions.get(extraction_id)
    if old is None:
        raise api_error("not_found", f"Không tìm thấy extraction {extraction_id}")
    if old.superseded_by is not None:
        raise api_error("invalid_state", "Extraction đã được chạy lại, hãy dùng bản mới")
    if old.status not in (STATUS_SUCCEEDED, STATUS_FAILED):
        raise api_error("invalid_state", "Chỉ chạy lại được extraction đã xong hoặc đã lỗi")
    llm_only = body.mode == MODE_LLM_ONLY
    if llm_only and not (old.ocr_clean or "").strip():
        raise api_error("invalid_state", "Bản cũ chưa có text OCR để chạy lại chỉ bằng LLM")

    prompt = resolve_prompt(state, body.prompt_id)
    new_id = uuid4().hex
    ocr_kwargs = ({"engine": old.engine, "ocr_raw": old.ocr_raw, "ocr_clean": old.ocr_clean}
                  if llm_only else {})
    try:
        records = copy_images(storage_dir, old.id, new_id, state.extractions.list_images(old.id))
        state.extractions.create(new_id, prompt.id, body.mode, records, rerun_of=old.id, **ocr_kwargs)
    except Exception:
        delete_images(storage_dir, new_id)
        raise
    return JSONResponse(status_code=202, content={"id": new_id, "status": STATUS_QUEUED})


@router.put("/extractions/{extraction_id}/feedback")
def put_feedback(extraction_id: str, body: FeedbackBody, request: Request):
    """Lưu đánh giá và bản duyệt, trả bảng độ lệch so với đề xuất (ghi đè khi gửi lại)."""
    state = request.app.state
    unknown = sorted(set(body.final_fields) - set(FIELD_KEYS))
    if unknown:
        raise api_error("invalid_request", f"Trường không hợp lệ: {', '.join(unknown)}")
    row = state.extractions.get(extraction_id)
    if row is None:
        raise api_error("not_found", f"Không tìm thấy extraction {extraction_id}")
    if row.status != STATUS_SUCCEEDED or row.superseded_by is not None:
        raise api_error("invalid_state", "Chỉ đánh giá được extraction đã thành công và chưa bị thay thế")
    final = {k: body.final_fields.get(k, "") for k in FIELD_KEYS}
    fields = row.result["fields"]
    proposed = {k: fields.get(k, {}).get("value", "") for k in FIELD_KEYS}
    diff = compare_fields(proposed, final, state.settings.minor_edit_threshold)
    state.feedback.upsert(extraction_id, body.rating, final, diff)
    return {"rating": body.rating, **diff}
