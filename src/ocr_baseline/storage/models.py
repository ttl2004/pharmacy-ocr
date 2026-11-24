"""Các dataclass trả về từ repository."""
from dataclasses import dataclass


@dataclass(frozen=True)
class ImageRecord:
    index: int
    path: str  # tương đối so với storage_dir
    width: int
    height: int
    bytes: int


@dataclass(frozen=True)
class ExtractionRow:
    id: str
    status: str
    error: str | None
    mode: str
    rerun_of: str | None
    superseded_by: str | None
    prompt_id: int
    engine: str | None
    llm_model: str | None
    ocr_raw: str | None
    ocr_clean: str | None
    result: dict | None
    created_at: str
    updated_at: str
    started_at: str | None
    finished_at: str | None


@dataclass(frozen=True)
class FeedbackRow:
    extraction_id: str
    rating: int
    final_fields: dict[str, str]
    diff: dict
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class StatsRow:
    prompt_id: int
    engine: str | None
    llm_model: str | None
    rating: int
    diff: dict
    sources: dict[str, str]  # field key -> source (lấy từ result.fields[k].source)
