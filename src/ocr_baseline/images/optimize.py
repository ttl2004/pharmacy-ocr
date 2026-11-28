"""Tối ưu ảnh về WebP và đọc ảnh thành mảng BGR cho OCR."""
import io
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from pillow_heif import register_heif_opener
from PIL import Image, ImageOps, UnidentifiedImageError

from .validation import UploadRejected

# Cho phép Image.open đọc HEIC/HEIF (ảnh iPhone); exif_transpose bên dưới vẫn xoay đúng chiều
register_heif_opener()


@dataclass(frozen=True)
class OptimizedImage:
    data: bytes
    width: int
    height: int


def _has_alpha(img: Image.Image) -> bool:
    return img.mode in ("RGBA", "LA", "PA", "La", "RGBa") or (img.mode == "P" and "transparency" in img.info)


def optimize_to_webp(data: bytes, max_side: int, quality: int) -> OptimizedImage:
    """Xoay theo EXIF, dán nền trắng nếu có alpha, thu nhỏ về max_side, lưu WebP."""
    try:
        with Image.open(io.BytesIO(data)) as src:
            img = ImageOps.exif_transpose(src)
            if _has_alpha(img):
                rgba = img.convert("RGBA")
                background = Image.new("RGB", rgba.size, (255, 255, 255))
                background.paste(rgba, mask=rgba.getchannel("A"))
                img = background
            else:
                img = img.convert("RGB")
            # thumbnail chỉ thu nhỏ, ảnh nhỏ hơn max_side giữ nguyên kích thước
            img.thumbnail((max_side, max_side), Image.LANCZOS)
            out = io.BytesIO()
            img.save(out, format="WEBP", quality=quality)
            return OptimizedImage(data=out.getvalue(), width=img.width, height=img.height)
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError, ValueError, SyntaxError) as e:
        raise UploadRejected("unsupported_format", f"Không đọc được ảnh: {e}") from e


def decode_image(data: bytes) -> np.ndarray:
    img = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Không đọc được file ảnh")
    return img


def load_bgr(path: Path) -> np.ndarray:
    # np.fromfile + imdecode thay cho cv2.imread để đọc được đường dẫn có dấu tiếng Việt
    return decode_image(np.fromfile(str(path), dtype=np.uint8).tobytes())
