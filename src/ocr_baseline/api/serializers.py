"""Chuyển dữ liệu lưu trữ thành JSON trả về của API."""
from ..constants import IMAGE_CONTENT_TYPE, STATUS_SUCCEEDED
from ..prompts import Prompt
from ..storage import ExtractionRow, FeedbackRow, ImageRecord


def feedback_to_json(f: FeedbackRow) -> dict:
    """Bản duyệt của người dùng kèm kết quả so sánh (lấy từ f.diff)."""
    return {
        "rating": f.rating,
        "final_fields": f.final_fields,
        "fields": f.diff.get("fields"),
        "summary": f.diff.get("summary"),
        "updated_at": f.updated_at,
    }


def extraction_to_json(row: ExtractionRow, images: list[ImageRecord], prompt: Prompt | None,
                       feedback: FeedbackRow | None) -> dict:
    """Chi tiết một extraction. `ocr` None khi chưa OCR, `result` None khi chưa succeeded."""
    has_ocr = row.ocr_raw is not None or row.ocr_clean is not None
    return {
        "id": row.id,
        "status": row.status,
        "error": row.error,
        "superseded_by": row.superseded_by,
        "engine": row.engine,
        "llm_model": row.llm_model,
        "prompt_version": prompt.version if prompt is not None else None,
        "images": [
            {"index": im.index, "content_type": IMAGE_CONTENT_TYPE, "width": im.width,
             "height": im.height, "bytes": im.bytes}
            for im in images
        ],
        "ocr": {"raw": row.ocr_raw or "", "clean": row.ocr_clean or ""} if has_ocr else None,
        "result": row.result if row.status == STATUS_SUCCEEDED else None,
        "feedback": feedback_to_json(feedback) if feedback is not None else None,
    }
