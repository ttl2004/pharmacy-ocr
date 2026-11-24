"""Kiểm tra ảnh tải lên: số lượng, dung lượng và định dạng thật (magic bytes)."""


class UploadRejected(Exception):
    """Ảnh tải lên bị từ chối. `code` khớp với mã lỗi của API."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def detect_format(data: bytes) -> str | None:
    """Nhận dạng định dạng theo magic bytes, không tin đuôi file."""
    if data[:3] == b"\xff\xd8\xff":
        return "jpeg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    return None


def check_count(n: int, max_images: int) -> None:
    if n == 0:
        raise UploadRejected("invalid_request", "Cần ít nhất 1 ảnh")
    if n > max_images:
        raise UploadRejected("too_many_images", f"Tối đa {max_images} ảnh, nhận được {n}")


def check_image(data: bytes, index: int, max_bytes: int) -> None:
    """`index` đếm từ 0."""
    if len(data) > max_bytes:
        raise UploadRejected(
            "image_too_large",
            f"Ảnh thứ {index} vượt quá {max_bytes // (1024 * 1024)} MB",
        )
    if detect_format(data) is None:
        raise UploadRejected(
            "unsupported_format",
            f"Ảnh thứ {index} không phải JPEG, PNG hoặc WebP",
        )
