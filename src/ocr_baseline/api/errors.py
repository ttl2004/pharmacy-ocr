"""Định dạng lỗi thống nhất: {"error": {"code", "message"}}."""
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

log = logging.getLogger(__name__)

ERROR_STATUS = {
    "too_many_images": 400,
    "image_too_large": 413,
    "unsupported_format": 415,
    "not_found": 404,
    "invalid_state": 409,
    "unauthorized": 401,
    "invalid_request": 422,
    "internal_error": 500,
}


class ApiError(Exception):
    """Lỗi nghiệp vụ, được chuyển thành JSON lỗi chuẩn."""

    def __init__(self, status_code: int, code: str, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


def api_error(code: str, message: str) -> ApiError:
    """Tạo ApiError với status lấy từ ERROR_STATUS (mã lạ thì 500)."""
    return ApiError(ERROR_STATUS.get(code, 500), code, message)


def _body(code: str, message: str) -> dict:
    return {"error": {"code": code, "message": message}}


def install_error_handlers(app: FastAPI) -> None:
    """Gắn các handler lỗi vào app."""

    @app.exception_handler(ApiError)
    async def _api_error(request: Request, exc: ApiError):
        return JSONResponse(status_code=exc.status_code, content=_body(exc.code, exc.message))

    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError):
        errors = exc.errors()
        if errors:
            first = errors[0]
            loc = ".".join(str(p) for p in first.get("loc", ()))
            msg = str(first.get("msg", "invalid"))
            message = f"{loc}: {msg}" if loc else msg
        else:
            message = "Yêu cầu không hợp lệ"
        return JSONResponse(status_code=ERROR_STATUS["invalid_request"], content=_body("invalid_request", message))

    @app.exception_handler(StarletteHTTPException)
    async def _http(request: Request, exc: StarletteHTTPException):
        # 404 -> not_found; các mã khác (405, ...) -> invalid_request, giữ nguyên status gốc.
        code = "not_found" if exc.status_code == 404 else "invalid_request"
        return JSONResponse(status_code=exc.status_code, content=_body(code, str(exc.detail)),
                            headers=getattr(exc, "headers", None))

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception):
        log.exception("Lỗi không xử lý được ở %s %s", request.method, request.url.path)
        return JSONResponse(status_code=500, content=_body("internal_error", "Lỗi nội bộ"))
