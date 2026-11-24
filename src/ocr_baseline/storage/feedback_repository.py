"""Đọc / ghi bảng feedback."""
import json
from pathlib import Path

from ..constants import STATUS_SUCCEEDED
from .database import connect, now_iso, write_transaction
from .models import FeedbackRow, StatsRow


def _dumps(value) -> str:
    return json.dumps(value, ensure_ascii=False)


def _row_to_feedback(row) -> FeedbackRow:
    return FeedbackRow(extraction_id=row["extraction_id"], rating=row["rating"],
                       final_fields=json.loads(row["final_fields_json"]), diff=json.loads(row["diff_json"]),
                       created_at=row["created_at"], updated_at=row["updated_at"])


class FeedbackRepository:
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)

    def upsert(self, extraction_id: str, rating: int, final_fields: dict[str, str], diff: dict) -> FeedbackRow:
        """Ghi đè feedback của extraction, giữ created_at cũ."""
        now = now_iso()
        with write_transaction(self.db_path) as conn:
            conn.execute(
                "INSERT INTO feedback (extraction_id, rating, final_fields_json, diff_json, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT(extraction_id) DO UPDATE SET "
                "rating = excluded.rating, final_fields_json = excluded.final_fields_json, "
                "diff_json = excluded.diff_json, updated_at = excluded.updated_at",
                (extraction_id, rating, _dumps(final_fields), _dumps(diff), now, now))
            row = conn.execute("SELECT * FROM feedback WHERE extraction_id = ?", (extraction_id,)).fetchone()
        return _row_to_feedback(row)

    def get(self, extraction_id: str) -> FeedbackRow | None:
        with connect(self.db_path) as conn:
            row = conn.execute("SELECT * FROM feedback WHERE extraction_id = ?", (extraction_id,)).fetchone()
        return _row_to_feedback(row) if row else None

    def list_for_stats(self) -> list[StatsRow]:
        """Feedback của extraction succeeded chưa bị thay thế (superseded_by IS NULL)."""
        sql = ("SELECT e.prompt_id, e.engine, e.llm_model, e.result_json, f.rating, f.diff_json "
               "FROM feedback f JOIN extractions e ON e.id = f.extraction_id "
               "WHERE e.status = ? AND e.superseded_by IS NULL ORDER BY f.created_at")
        with connect(self.db_path) as conn:
            rows = conn.execute(sql, (STATUS_SUCCEEDED,)).fetchall()
        stats = []
        for r in rows:
            fields = (json.loads(r["result_json"]) if r["result_json"] else {}).get("fields") or {}
            sources = {k: v.get("source") for k, v in fields.items() if isinstance(v, dict)}
            stats.append(StatsRow(prompt_id=r["prompt_id"], engine=r["engine"], llm_model=r["llm_model"],
                                  rating=r["rating"], diff=json.loads(r["diff_json"]), sources=sources))
        return stats
