"""Xác thực bằng header X-API-Key."""
import secrets

from fastapi import Header, Request

from .errors import api_error


def require_api_key(request: Request, x_api_key: str | None = Header(None, alias="X-API-Key")) -> None:
    """Dependency: so sánh key an toàn thời gian. Sai hoặc thiếu thì báo unauthorized."""
    expected = request.app.state.settings.api_key
    if x_api_key is None or not secrets.compare_digest(x_api_key.encode(), expected.encode()):
        raise api_error("unauthorized", "API key không hợp lệ")
