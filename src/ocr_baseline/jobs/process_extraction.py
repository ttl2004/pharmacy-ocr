"""Xử lý một extraction: ảnh -> OCR -> làm sạch -> LLM -> lưu kết quả."""
import logging
import threading
from typing import Callable

from ..config import Settings
from ..constants import MODE_FULL
from ..extraction import LlmError
from ..images import image_file, load_bgr
from ..ocr import OcrError, create_engine
from ..pipeline import build_result, run_ocr
from ..storage import ExtractionRepository, PromptRepository
from ..text import clean_ocr_text

logger = logging.getLogger(__name__)

# Mỗi thread worker giữ cache engine riêng {method: engine}, vì engine local không an toàn khi dùng chung thread.
_local = threading.local()


def _engine_getter(settings: Settings) -> Callable[[str], object]:
    """Trả hàm lấy engine theo tên từ cache của thread hiện tại, tạo lười khi dùng lần đầu."""
    def get_engine(method: str):
        cache = getattr(_local, "engines", None)
        if cache is None:
            cache = _local.engines = {}
        if method not in cache:
            # Tạo lỗi (vd OcrUnavailableError) thì chưa gán vào cache nên lần sau sẽ thử lại
            cache[method] = create_engine(method, settings)
        return cache[method]
    return get_engine


def make_handler(settings: Settings, extractions: ExtractionRepository,
                 prompts: PromptRepository) -> Callable[[str], None]:
    """Tạo handler nhận id extraction. OcrError/LlmError ghi thành failed; lỗi khác để JobRunner xử lý."""
    get_engine = _engine_getter(settings)

    def handle(id: str) -> None:
        row = extractions.get(id)
        if row is None:
            logger.info("Extraction %s không còn tồn tại, bỏ qua", id)
            return
        prompt = prompts.get(row.prompt_id)
        if prompt is None:
            extractions.mark_failed(id, "Không tìm thấy prompt")
            return
        try:
            if row.mode == MODE_FULL:
                images = [load_bgr(image_file(settings.storage_dir, rec)) for rec in extractions.list_images(id)]
                outcome = run_ocr(images, settings, get_engine)
                ocr_clean = clean_ocr_text(outcome.raw)
                extractions.mark_ocr(id, outcome.engine, outcome.raw, ocr_clean)
            else:
                # llm_only: dùng lại text đã chép lúc rerun
                ocr_clean = row.ocr_clean or ""
            if not ocr_clean.strip():
                extractions.mark_failed(id, "OCR không đọc được chữ nào")
                return
            result, llm_model = build_result(ocr_clean, prompt, settings)
            extractions.mark_succeeded(id, llm_model, result)
        except (OcrError, LlmError) as e:
            extractions.mark_failed(id, str(e))

    return handle
