"""Middleware chặn sớm: kiểm tra API key và kích thước body trước khi FastAPI parse multipart."""
import secrets

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from ..config import Settings
from .errors import ERROR_STATUS, _body

_API_PREFIX = "/api/v1"
_OVERHEAD_BYTES = 1024 * 1024  # dư cho các field form và boundary


def install_request_guard(app: FastAPI, settings: Settings) -> None:
    """Gắn middleware cho các đường dẫn /api/v1; dependency require_api_key vẫn giữ nguyên."""
    max_body = settings.max_images * settings.max_image_bytes + _OVERHEAD_BYTES

    @app.middleware("http")
    async def _guard(request: Request, call_next):
        if request.url.path.startswith(_API_PREFIX):
            key = request.headers.get("X-API-Key")
            if key is None or not secrets.compare_digest(key.encode(), settings.api_key.encode()):
                return JSONResponse(status_code=ERROR_STATUS["unauthorized"],
                                    content=_body("unauthorized", "API key không hợp lệ"))
            length = request.headers.get("content-length")
            if length and length.isdigit() and int(length) > max_body:
                return JSONResponse(status_code=ERROR_STATUS["image_too_large"],
                                    content=_body("image_too_large", "Nội dung yêu cầu quá lớn"))
        return await call_next(request)
