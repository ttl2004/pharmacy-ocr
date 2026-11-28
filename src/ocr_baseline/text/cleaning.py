"""Làm sạch văn bản OCR bằng quy tắc, không dùng LLM và không động vào chữ số."""

import re
import unicodedata

# Khoảng trắng ngang (gồm cả NBSP) cần gom thành một dấu cách
_SPACES = re.compile(r"[ \t ]+")
# Dòng kết thúc bằng các ký tự này coi như đã hết câu, không nối dòng sau
_SENTENCE_END = ".:;!?)"


def clean_ocr_text(raw: str) -> str:
    """Làm sạch `ocr_raw` thành `ocr_clean`.

    Thứ tự: chuẩn hoá NFC và xuống dòng, gom khoảng trắng từng dòng, ghép
    dòng bị ngắt (gạch nối cuối dòng được ưu tiên hơn nối thường), gom dòng
    rỗng và strip toàn văn bản. Dòng rỗng là ranh giới đoạn.

    Ví dụ:
        "Para-\ncetamol 500\nmg" -> "Paracetamol 500 mg"
        "Chỉ định:\nGiảm đau" -> giữ nguyên 2 dòng vì "G" viết hoa
    """
    text = unicodedata.normalize("NFC", raw)
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    out: list[str] = []
    for line in text.split("\n"):
        cur = _SPACES.sub(" ", line).strip()
        if not cur:
            # Gom nhiều dòng rỗng liên tiếp thành một
            if out and out[-1] != "":
                out.append("")
            continue
        # prev là dòng liền trước (đã có thể là kết quả của lần ghép trước)
        prev = out[-1] if out else ""
        if prev and cur[0].islower():
            if prev.endswith("-") and len(prev) > 1 and prev[-2].isalpha():
                # Bỏ gạch nối cuối dòng, dính hai nửa từ lại
                out[-1] = prev[:-1] + cur
                continue
            if not prev.endswith(tuple(_SENTENCE_END)):
                # Dòng bị ngắt giữa câu, nối bằng một dấu cách
                out[-1] = prev + " " + cur
                continue
        out.append(cur)

    return "\n".join(out).strip()
