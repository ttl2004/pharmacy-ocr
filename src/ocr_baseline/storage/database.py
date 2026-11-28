"""Kết nối SQLite và định nghĩa bảng.

- prompts           : prompt cho LLM, có phiên bản (mỗi lần sửa = một dòng mới), đúng một prompt active.
- extractions       : mỗi lần trích xuất (một hàng đợi công việc + kết quả).
- extraction_images : ảnh đã tối ưu của extraction (path tương đối so với storage_dir).
- feedback          : đánh giá và bản chỉnh sửa cuối của người dùng cho extraction.
"""
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS prompts (
  id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, version INTEGER NOT NULL,
  content TEXT NOT NULL, note TEXT NOT NULL DEFAULT '',
  is_builtin INTEGER NOT NULL DEFAULT 0, is_active INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL, UNIQUE (name, version));
CREATE UNIQUE INDEX IF NOT EXISTS idx_prompts_one_active ON prompts(is_active) WHERE is_active = 1;

CREATE TABLE IF NOT EXISTS extractions (
  id TEXT PRIMARY KEY,
  status TEXT NOT NULL CHECK (status IN ('queued','running','succeeded','failed')),
  error TEXT, mode TEXT NOT NULL CHECK (mode IN ('full','llm_only')),
  rerun_of TEXT, superseded_by TEXT,          -- không đặt FK: xoá bản cũ không ảnh hưởng bản mới
  prompt_id INTEGER NOT NULL REFERENCES prompts(id),
  engine TEXT, llm_model TEXT, ocr_raw TEXT, ocr_clean TEXT, result_json TEXT,
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL, started_at TEXT, finished_at TEXT);
CREATE INDEX IF NOT EXISTS idx_extractions_status_created ON extractions(status, created_at);

CREATE TABLE IF NOT EXISTS extraction_images (
  extraction_id TEXT NOT NULL REFERENCES extractions(id) ON DELETE CASCADE,
  idx INTEGER NOT NULL, path TEXT NOT NULL,   -- path tương đối so với storage_dir
  width INTEGER NOT NULL, height INTEGER NOT NULL, bytes INTEGER NOT NULL,
  PRIMARY KEY (extraction_id, idx));

CREATE TABLE IF NOT EXISTS feedback (
  extraction_id TEXT PRIMARY KEY REFERENCES extractions(id) ON DELETE CASCADE,
  rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
  final_fields_json TEXT NOT NULL, diff_json TEXT NOT NULL,
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
"""


def now_iso() -> str:
    """Thời gian hiện tại, ISO UTC."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@contextmanager
def connect(db_path: Path):
    """Mở kết nối, tự commit khi thành công, rollback khi lỗi, luôn đóng kết nối.

    Mỗi lần gọi là một kết nối riêng (an toàn cho nhiều thread).
    """
    conn = sqlite3.connect(db_path, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 10000")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


@contextmanager
def write_transaction(db_path: Path):
    """Kết nối với transaction ghi tường minh (`BEGIN IMMEDIATE`).

    BEGIN IMMEDIATE lấy khoá ghi ngay từ đầu, nên đọc rồi ghi trong cùng khối không bị
    thread khác chen vào giữa (cần cho claim_next, tính version prompt...).
    """
    with connect(db_path) as conn:
        conn.isolation_level = None  # tắt transaction ngầm của module sqlite3, tự BEGIN/COMMIT
        conn.execute("BEGIN IMMEDIATE")
        try:
            yield conn
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise


def init_db(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with connect(db_path) as conn:
        conn.execute("PRAGMA journal_mode = WAL")
        conn.executescript(SCHEMA)
