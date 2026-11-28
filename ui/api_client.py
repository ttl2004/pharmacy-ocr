"""HTTP client gọi OCR service. Streamlit đóng vai backend, chỉ nói chuyện với service qua HTTP."""
import os
from pathlib import Path

import requests
import streamlit as st
from dotenv import load_dotenv

# Thư mục gốc dự án (chứa .env)
PROJECT_ROOT = Path(__file__).resolve().parents[1]


class ServiceError(Exception):
    """Lỗi do service trả về (status khác 2xx) hoặc body lỗi sai dạng."""

    def __init__(self, status: int, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.status = status
        self.code = code
        self.message = message


def _to_service_error(resp: requests.Response) -> ServiceError:
    """Đọc body {"error": {"code", "message"}}; sai dạng thì code = http_error."""
    try:
        err = resp.json()["error"]
        return ServiceError(resp.status_code, str(err["code"]), str(err["message"]))
    except (ValueError, KeyError, TypeError):
        return ServiceError(resp.status_code, "http_error", resp.text[:300] or resp.reason or "")


class OcrServiceClient:
    """Mỗi method ứng với một endpoint của service."""

    def __init__(self, base_url: str, api_key: str, timeout: float = 60):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    def _request(self, method: str, path: str, **kwargs) -> requests.Response:
        """Gửi request kèm X-API-Key; response khác 2xx thì raise ServiceError."""
        headers = {"X-API-Key": self.api_key}
        try:
            resp = requests.request(method, self.base_url + path, headers=headers,
                                    timeout=self.timeout, **kwargs)
        except requests.RequestException as exc:
            raise ServiceError(0, "connection_error", str(exc)) from exc
        if not 200 <= resp.status_code < 300:
            raise _to_service_error(resp)
        return resp

    def create_extraction(self, files: list[tuple[str, bytes, str]],
                          prompt_id: int | None) -> dict:
        """files: danh sách (tên file, bytes, mime), theo thứ tự ghép văn bản."""
        multipart = [("images[]", (name, data, mime)) for name, data, mime in files]
        form = {"prompt_id": str(prompt_id)} if prompt_id is not None else None
        return self._request("POST", "/extractions", files=multipart, data=form).json()

    def get_extraction(self, extraction_id: str) -> dict:
        return self._request("GET", f"/extractions/{extraction_id}").json()

    def get_image(self, extraction_id: str, index: int) -> bytes:
        return self._request("GET", f"/extractions/{extraction_id}/images/{index}").content

    def rerun(self, extraction_id: str, mode: str, prompt_id: int | None = None) -> dict:
        body: dict = {"mode": mode}
        if prompt_id is not None:
            body["prompt_id"] = prompt_id
        return self._request("POST", f"/extractions/{extraction_id}/rerun", json=body).json()

    def put_feedback(self, extraction_id: str, rating: int, final_fields: dict) -> dict:
        body = {"rating": rating, "final_fields": final_fields}
        return self._request("PUT", f"/extractions/{extraction_id}/feedback", json=body).json()

    def delete(self, extraction_id: str) -> None:
        self._request("DELETE", f"/extractions/{extraction_id}")

    def stats(self, group_by: str) -> dict:
        return self._request("GET", "/stats", params={"group_by": group_by}).json()

    def parse(self, fields: dict) -> dict:
        return self._request("POST", "/parse", json={"fields": fields}).json()

    def list_prompts(self) -> list[dict]:
        return self._request("GET", "/prompts").json()

    def create_prompt(self, name: str, content: str, note: str) -> dict:
        body = {"name": name, "content": content, "note": note}
        return self._request("POST", "/prompts", json=body).json()

    def activate_prompt(self, prompt_id: int) -> dict:
        return self._request("POST", f"/prompts/{prompt_id}/activate").json()


@st.cache_resource
def get_client() -> OcrServiceClient:
    """Đọc .env ở thư mục gốc rồi tạo client (cache theo phiên Streamlit)."""
    load_dotenv(PROJECT_ROOT / ".env")
    base = os.getenv("OCR_SERVICE_URL", "http://127.0.0.1:8000").rstrip("/")
    return OcrServiceClient(base + "/api/v1", os.getenv("OCR_SERVICE_API_KEY", ""))
