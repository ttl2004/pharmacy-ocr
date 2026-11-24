"""Các bước xử lý dùng chung: ảnh -> OCR (Vision, dự phòng local) -> ghép trường -> kết quả."""
import logging
from dataclasses import dataclass
from typing import Any, Callable

import numpy as np

from .config import Settings
from .constants import (ENGINE_LOCAL, ENGINE_VISION, SCHEMA_VERSION, SOURCE_LLM, SOURCE_NONE,
                        SOURCE_SECTION, STRUCTURED_FIELDS)
from .extraction import extract_fields, unverified_numbers
from .ocr import OcrUnavailableError
from .profiles import DRUG_PROFILE, FIELD_KEYS
from .prompts import Prompt
from .text import parse_structured, split_sections

logger = logging.getLogger(__name__)


@dataclass
class OcrOutcome:
    """Kết quả OCR của cả extraction: engine thực tế đã dùng và text thô đã ghép."""
    engine: str
    raw: str


def _ocr_all(engine, images: list[np.ndarray]) -> str:
    """Chạy một engine cho mọi ảnh theo thứ tự, ghép text các ảnh không rỗng bằng dòng trống."""
    texts = [engine.run(img).text for img in images]
    return "\n\n".join(t for t in texts if t)


def run_ocr(images: list[np.ndarray], settings: Settings, get_engine: Callable[[str], Any]) -> OcrOutcome:
    """OCR toàn bộ ảnh bằng `settings.ocr_engine`. Vision không dùng được thì làm lại tất cả ảnh bằng local."""
    name = settings.ocr_engine
    try:
        return OcrOutcome(engine=name, raw=_ocr_all(get_engine(name), images))
    except OcrUnavailableError as e:
        if name != ENGINE_VISION:
            raise
        logger.warning("Vision không dùng được (%s), chuyển sang OCR local", e)
    return OcrOutcome(engine=ENGINE_LOCAL, raw=_ocr_all(get_engine(ENGINE_LOCAL), images))


def assemble_fields(llm_fields: dict[str, str], sections: dict[str, str], ocr_clean: str) -> dict[str, dict]:
    """Ghép từng trường: ưu tiên mục tách theo tiêu đề, sau đó LLM; kèm cảnh báo số không có trong OCR."""
    result = {}
    for key in FIELD_KEYS:
        if key in sections:
            value, source = sections[key], SOURCE_SECTION
        else:
            value = llm_fields.get(key) or ""
            source = SOURCE_LLM if value else SOURCE_NONE
        warnings = unverified_numbers({key: value}, ocr_clean).get(key, [])
        result[key] = {"value": value, "source": source, "warnings": warnings}
    return result


def build_result(ocr_clean: str, prompt: Prompt, settings: Settings) -> tuple[dict, str]:
    """Gọi LLM, tách mục (nếu bật), dựng result. Trả về (result, tên model LLM)."""
    llm_fields, info = extract_fields(ocr_clean, DRUG_PROFILE, prompt.content, settings)
    sections = None
    if settings.section_split_enabled:
        sections = split_sections(ocr_clean, settings.section_min_found)
    fields = assemble_fields(llm_fields, sections or {}, ocr_clean)
    result = {
        "schema_version": SCHEMA_VERSION,
        "fields": fields,
        "structured": parse_structured({k: fields[k]["value"] for k in STRUCTURED_FIELDS}),
    }
    return result, info["model"]
