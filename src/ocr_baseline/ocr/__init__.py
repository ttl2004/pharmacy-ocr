"""Bước OCR: ảnh -> text. Mọi engine có hàm `run(img_bgr) -> OcrResult` và thuộc tính `name`.

Thêm hướng OCR mới:
    1. Viết class có `run()` và `name` (xem vision.py).
    2. Thêm mã engine vào constants.py (ENGINE_...).
    3. Thêm nhánh trong create_engine() bên dưới.
"""
from ..config import Settings
from ..constants import ENGINE_LOCAL, ENGINE_VISION
from .errors import OcrError, OcrImageError, OcrUnavailableError
from .types import OcrLine, OcrResult

__all__ = ["OcrError", "OcrImageError", "OcrLine", "OcrResult", "OcrUnavailableError", "create_engine"]


def create_engine(method: str, settings: Settings):
    if method == ENGINE_VISION:
        from .vision import VisionEngine

        return VisionEngine(settings.google_vision_api_key, timeout=settings.vision_timeout)

    if method == ENGINE_LOCAL:
        from .local import LocalOcrEngine  # import chậm (Paddle, torch) -> chỉ import khi cần

        return LocalOcrEngine(settings.models_dir, threads=settings.ocr_threads,
                              enable_mkldnn=settings.ocr_enable_mkldnn,
                              det_limit_side_len=settings.ocr_det_limit_side)

    raise ValueError(f"Cách thực hiện không hợp lệ: {method}")
