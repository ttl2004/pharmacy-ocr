"""Đọc / ghi bảng prompts."""
from pathlib import Path

from ..prompts import Prompt, builtin_prompt
from .database import connect, now_iso, write_transaction


def _row_to_prompt(row) -> Prompt:
    return Prompt(id=row["id"], name=row["name"], version=row["version"], content=row["content"],
                  note=row["note"], is_builtin=bool(row["is_builtin"]),
                  is_active=bool(row["is_active"]), created_at=row["created_at"])


class PromptRepository:
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)

    def seed_builtin(self) -> None:
        """Bảng rỗng thì thêm prompt gốc (version 1, builtin, active)."""
        name, content = builtin_prompt()
        with write_transaction(self.db_path) as conn:
            if conn.execute("SELECT COUNT(*) FROM prompts").fetchone()[0] == 0:
                conn.execute(
                    "INSERT INTO prompts (name, version, content, note, is_builtin, is_active, created_at) "
                    "VALUES (?, 1, ?, 'Prompt gốc từ code', 1, 1, ?)", (name, content, now_iso()))

    def list(self) -> list[Prompt]:
        with connect(self.db_path) as conn:
            rows = conn.execute("SELECT * FROM prompts ORDER BY name, version").fetchall()
        return [_row_to_prompt(r) for r in rows]

    def get(self, prompt_id: int) -> Prompt | None:
        with connect(self.db_path) as conn:
            row = conn.execute("SELECT * FROM prompts WHERE id = ?", (prompt_id,)).fetchone()
        return _row_to_prompt(row) if row else None

    def get_active(self) -> Prompt:
        with connect(self.db_path) as conn:
            row = conn.execute("SELECT * FROM prompts WHERE is_active = 1").fetchone()
        if row is None:
            raise RuntimeError("Không có prompt nào đang active (chưa seed_builtin?)")
        return _row_to_prompt(row)

    def create(self, name: str, content: str, note: str) -> Prompt:
        """Thêm version mới (max version cùng name + 1), chưa active."""
        with write_transaction(self.db_path) as conn:
            version = (conn.execute("SELECT MAX(version) FROM prompts WHERE name = ?",
                                    (name,)).fetchone()[0] or 0) + 1
            cur = conn.execute(
                "INSERT INTO prompts (name, version, content, note, is_builtin, is_active, created_at) "
                "VALUES (?, ?, ?, ?, 0, 0, ?)", (name, version, content, note, now_iso()))
            row = conn.execute("SELECT * FROM prompts WHERE id = ?", (cur.lastrowid,)).fetchone()
        return _row_to_prompt(row)

    def activate(self, prompt_id: int) -> Prompt | None:
        """Đặt prompt thành active (và bỏ active của các prompt khác) trong một transaction."""
        with write_transaction(self.db_path) as conn:
            if conn.execute("SELECT 1 FROM prompts WHERE id = ?", (prompt_id,)).fetchone() is None:
                return None
            conn.execute("UPDATE prompts SET is_active = 0 WHERE is_active = 1")
            conn.execute("UPDATE prompts SET is_active = 1 WHERE id = ?", (prompt_id,))
            row = conn.execute("SELECT * FROM prompts WHERE id = ?", (prompt_id,)).fetchone()
        return _row_to_prompt(row)
