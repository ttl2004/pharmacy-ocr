"""Xử lý văn bản OCR: làm sạch, tách mục, parser cấu trúc."""

from .cleaning import clean_ocr_text
from .parsers import parse_structured
from .sections import fold, split_sections

__all__ = ["clean_ocr_text", "split_sections", "fold", "parse_structured"]
