"""Cấu hình đọc từ file .env.

Mọi nơi trong code lấy cấu hình qua `get_settings()`, không đọc os.environ trực tiếp.
"""
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[2]


def _default_threads() -> int:
    # Dùng hết số luồng logic thường CHẬM hơn (hyper-threading, nhân E).
    # Mặc định: một nửa số luồng, tối đa 4.
    cpu_count = os.cpu_count() or 2
    return max(1, min(4, cpu_count // 2))


def _to_bool(value: str) -> bool:
    return value.strip().lower() in ("1", "true", "yes")


@dataclass(frozen=True)
class Settings:
    # Bảo vệ API: bắt buộc, rỗng thì service không khởi động
    api_key: str

    # LLM (DeepSeek, API tương thích OpenAI)
    deepseek_api_key: str
    deepseek_base_url: str
    deepseek_model: str
    llm_timeout: float

    # Google Cloud Vision
    google_vision_api_key: str
    vision_timeout: float

    # Đường dẫn
    data_dir: Path
    db_path: Path
    storage_dir: Path      # nơi lưu ảnh đã tối ưu của từng extraction
    models_dir: Path       # model VietOCR

    # OCR local
    ocr_threads: int
    ocr_enable_mkldnn: bool
    ocr_det_limit_side: int

    # Engine OCR mặc định: vision | local
    ocr_engine: str

    # Hàng đợi / worker
    worker_count: int
    worker_poll_seconds: float

    # Giới hạn và tối ưu ảnh tải lên
    max_images: int
    max_image_bytes: int
    image_max_side: int
    image_quality: int

    # Tách đoạn theo tiêu đề
    section_split_enabled: bool
    section_min_found: int

    # Ngưỡng tương đồng để coi là sửa nhẹ (feedback)
    minor_edit_threshold: float


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    load_dotenv(ROOT_DIR / ".env")
    env = os.getenv
    data_dir = Path(env("DATA_DIR", str(ROOT_DIR / "data")))
    return Settings(
        api_key=env("OCR_SERVICE_API_KEY", "").strip(),
        deepseek_api_key=env("DEEPSEEK_API_KEY", "").strip(),
        deepseek_base_url=env("DEEPSEEK_BASE_URL", "https://api.deepseek.com").strip(),
        deepseek_model=env("DEEPSEEK_MODEL", "deepseek-chat").strip(),
        llm_timeout=float(env("LLM_TIMEOUT", "180")),
        google_vision_api_key=env("GOOGLE_VISION_API_KEY", "").strip(),
        vision_timeout=float(env("VISION_TIMEOUT", "60")),
        data_dir=data_dir,
        db_path=Path(env("DB_PATH", str(data_dir / "ocr_service.db"))),
        storage_dir=Path(env("STORAGE_DIR", str(data_dir / "extractions"))),
        models_dir=Path(env("MODELS_DIR", str(ROOT_DIR / "models"))),
        ocr_threads=int(env("OCR_THREADS", "0")) or _default_threads(),
        ocr_enable_mkldnn=_to_bool(env("OCR_ENABLE_MKLDNN", "true")),
        ocr_det_limit_side=int(env("OCR_DET_LIMIT_SIDE", "1600")),
        ocr_engine=env("OCR_ENGINE", "vision").strip(),
        worker_count=int(env("WORKER_COUNT", "1")),
        worker_poll_seconds=float(env("WORKER_POLL_SECONDS", "1.0")),
        max_images=int(env("MAX_IMAGES", "20")),
        max_image_bytes=int(env("MAX_IMAGE_MB", "5")) * 1024 * 1024,
        image_max_side=int(env("IMAGE_MAX_SIDE", "2400")),
        image_quality=int(env("IMAGE_QUALITY", "85")),
        section_split_enabled=_to_bool(env("SECTION_SPLIT_ENABLED", "false")),
        section_min_found=int(env("SECTION_MIN_FOUND", "3")),
        minor_edit_threshold=float(env("MINOR_EDIT_THRESHOLD", "0.9")),
    )
