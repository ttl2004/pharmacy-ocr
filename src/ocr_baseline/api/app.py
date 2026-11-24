"""Khung ứng dụng FastAPI.

Chạy: uvicorn ocr_baseline.api.app:create_app --factory --port 8000
(Không có biến module `app` để import không lỗi khi .env thiếu OCR_SERVICE_API_KEY.)
"""
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI

from ..config import Settings, get_settings
from ..jobs import JobRunner, make_handler
from ..storage import ExtractionRepository, FeedbackRepository, PromptRepository, init_db
from .auth import require_api_key
from .errors import install_error_handlers
from .routes_extractions import router as extractions_router
from .routes_prompts import router as prompts_router
from .routes_stats_parse import router as stats_parse_router


def create_app(settings: Settings | None = None) -> FastAPI:
    """Tạo app. Thiếu api_key thì lỗi ngay để không vô tình mở API không xác thực."""
    settings = settings or get_settings()
    if not settings.api_key:
        raise RuntimeError("Thiếu OCR_SERVICE_API_KEY trong .env")

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        init_db(settings.db_path)
        app.state.prompts.seed_builtin()
        settings.storage_dir.mkdir(parents=True, exist_ok=True)
        handler = make_handler(settings, app.state.extractions, app.state.prompts)
        runner = JobRunner(app.state.extractions, handler, settings.worker_count, settings.worker_poll_seconds)
        app.state.runner = runner
        runner.start()
        try:
            yield
        finally:
            runner.stop()

    app = FastAPI(title="Pharmacy OCR Service", lifespan=lifespan)
    app.state.settings = settings
    app.state.extractions = ExtractionRepository(settings.db_path)
    app.state.prompts = PromptRepository(settings.db_path)
    app.state.feedback = FeedbackRepository(settings.db_path)
    install_error_handlers(app)
    app.include_router(extractions_router, prefix="/api/v1", dependencies=[Depends(require_api_key)])
    app.include_router(stats_parse_router, prefix="/api/v1", dependencies=[Depends(require_api_key)])
    app.include_router(prompts_router, prefix="/api/v1", dependencies=[Depends(require_api_key)])
    return app
