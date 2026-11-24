"""Đọc / ghi bảng extractions và extraction_images (kiêm hàng đợi công việc)."""
import json
from pathlib import Path

from ..constants import STATUS_FAILED, STATUS_QUEUED, STATUS_RUNNING, STATUS_SUCCEEDED
from .database import connect, now_iso, write_transaction
from .models import ExtractionRow, ImageRecord


def _row_to_extraction(row) -> ExtractionRow:
    result = row["result_json"]
    return ExtractionRow(
        id=row["id"], status=row["status"], error=row["error"], mode=row["mode"],
        rerun_of=row["rerun_of"], superseded_by=row["superseded_by"], prompt_id=row["prompt_id"],
        engine=row["engine"], llm_model=row["llm_model"], ocr_raw=row["ocr_raw"],
        ocr_clean=row["ocr_clean"], result=json.loads(result) if result else None,
        created_at=row["created_at"], updated_at=row["updated_at"],
        started_at=row["started_at"], finished_at=row["finished_at"])


class ExtractionRepository:
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)

    def create(self, id: str, prompt_id: int, mode: str, images: list[ImageRecord], *,
               rerun_of: str | None = None, engine: str | None = None,
               ocr_raw: str | None = None, ocr_clean: str | None = None) -> None:
        """Tạo extraction ở trạng thái queued. Có rerun_of thì đánh dấu bản cũ bị thay thế (cùng transaction)."""
        now = now_iso()
        with write_transaction(self.db_path) as conn:
            conn.execute(
                "INSERT INTO extractions (id, status, mode, rerun_of, prompt_id, engine, ocr_raw, ocr_clean, "
                "created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (id, STATUS_QUEUED, mode, rerun_of, prompt_id, engine, ocr_raw, ocr_clean, now, now))
            conn.executemany(
                "INSERT INTO extraction_images (extraction_id, idx, path, width, height, bytes) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                [(id, i.index, i.path, i.width, i.height, i.bytes) for i in images])
            if rerun_of:
                conn.execute("UPDATE extractions SET superseded_by = ?, updated_at = ? WHERE id = ?",
                             (id, now, rerun_of))

    def get(self, id: str) -> ExtractionRow | None:
        with connect(self.db_path) as conn:
            row = conn.execute("SELECT * FROM extractions WHERE id = ?", (id,)).fetchone()
        return _row_to_extraction(row) if row else None

    def list_images(self, id: str) -> list[ImageRecord]:
        with connect(self.db_path) as conn:
            rows = conn.execute("SELECT * FROM extraction_images WHERE extraction_id = ? ORDER BY idx",
                                (id,)).fetchall()
        return [ImageRecord(index=r["idx"], path=r["path"], width=r["width"], height=r["height"],
                            bytes=r["bytes"]) for r in rows]

    def claim_next(self) -> str | None:
        """Lấy bản queued cũ nhất, đổi sang running. An toàn khi nhiều worker thread.

        Mỗi lệnh gọi mở kết nối riêng; BEGIN IMMEDIATE lấy khoá ghi trước khi SELECT, nên hai thread
        không thể cùng chọn một bản (thread sau chờ busy_timeout rồi thấy bản đó đã running).
        """
        with write_transaction(self.db_path) as conn:
            row = conn.execute("SELECT id FROM extractions WHERE status = ? ORDER BY created_at, rowid LIMIT 1",
                               (STATUS_QUEUED,)).fetchone()
            if row is None:
                return None
            now = now_iso()
            conn.execute("UPDATE extractions SET status = ?, started_at = ?, updated_at = ? WHERE id = ?",
                         (STATUS_RUNNING, now, now, row["id"]))
            return row["id"]

    def requeue_running(self) -> int:
        """Đưa các bản running (do service tắt đột ngột) về queued. Trả về số bản đã đưa lại."""
        with connect(self.db_path) as conn:
            cur = conn.execute("UPDATE extractions SET status = ?, started_at = NULL, updated_at = ? "
                               "WHERE status = ?", (STATUS_QUEUED, now_iso(), STATUS_RUNNING))
            return cur.rowcount

    def mark_ocr(self, id: str, engine: str, ocr_raw: str, ocr_clean: str) -> None:
        with connect(self.db_path) as conn:
            conn.execute("UPDATE extractions SET engine = ?, ocr_raw = ?, ocr_clean = ?, updated_at = ? "
                         "WHERE id = ?", (engine, ocr_raw, ocr_clean, now_iso(), id))

    def mark_succeeded(self, id: str, llm_model: str, result: dict) -> None:
        now = now_iso()
        with connect(self.db_path) as conn:
            conn.execute("UPDATE extractions SET status = ?, error = NULL, llm_model = ?, result_json = ?, "
                         "finished_at = ?, updated_at = ? WHERE id = ?",
                         (STATUS_SUCCEEDED, llm_model, json.dumps(result, ensure_ascii=False), now, now, id))

    def mark_failed(self, id: str, error: str) -> None:
        now = now_iso()
        with connect(self.db_path) as conn:
            conn.execute("UPDATE extractions SET status = ?, error = ?, finished_at = ?, updated_at = ? "
                         "WHERE id = ?", (STATUS_FAILED, error, now, now, id))

    def delete(self, id: str) -> None:
        """Xoá extraction; ảnh và feedback tự xoá theo ON DELETE CASCADE."""
        with connect(self.db_path) as conn:
            conn.execute("DELETE FROM extractions WHERE id = ?", (id,))
