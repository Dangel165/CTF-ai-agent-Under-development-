from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

import aiosqlite


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class JobStore:
    def __init__(self, db_path: str):
        self.db_path = db_path

    async def init(self) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    kind TEXT NOT NULL,
                    challenge_id INTEGER,
                    challenge_name TEXT,
                    challenge_dir TEXT,
                    spec_json TEXT,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    requested_by TEXT,
                    channel_id TEXT,
                    result_json TEXT,
                    log_path TEXT
                )
                """
            )
            try:
                await db.execute("ALTER TABLE jobs ADD COLUMN spec_json TEXT")
            except Exception:
                pass
            await db.commit()

    async def create_solve_job(
        self,
        *,
        challenge_name: str,
        spec: dict[str, Any],
        requested_by: str,
        channel_id: int,
        challenge_id: int | None = None,
    ) -> str:
        job_id = uuid.uuid4().hex[:12]
        now = _now()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO jobs (
                    id, kind, challenge_id, challenge_name, spec_json, status,
                    created_at, updated_at, requested_by, channel_id
                ) VALUES (?, 'solve', ?, ?, ?, 'queued', ?, ?, ?, ?)
                """,
                (
                    job_id,
                    challenge_id,
                    challenge_name,
                    json.dumps(spec, ensure_ascii=False),
                    now,
                    now,
                    requested_by,
                    str(channel_id),
                ),
            )
            await db.commit()
        return job_id

    async def mark(
        self,
        job_id: str,
        *,
        status: str,
        challenge_dir: str | None = None,
        result: dict[str, Any] | None = None,
        log_path: str | None = None,
    ) -> None:
        now = _now()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                UPDATE jobs
                SET status = ?, updated_at = ?,
                    challenge_dir = COALESCE(?, challenge_dir),
                    result_json = COALESCE(?, result_json),
                    log_path = COALESCE(?, log_path)
                WHERE id = ?
                """,
                (
                    status,
                    now,
                    challenge_dir,
                    json.dumps(result, ensure_ascii=False) if result is not None else None,
                    log_path,
                    job_id,
                ),
            )
            await db.commit()

    async def get(self, job_id: str) -> dict[str, Any] | None:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
            row = await cur.fetchone()
            if row is None:
                return None
            data = dict(row)
            if data.get("result_json"):
                data["result"] = json.loads(data["result_json"])
            if data.get("spec_json"):
                data["spec"] = json.loads(data["spec_json"])
            return data

    async def list_recent(self, limit: int = 10) -> list[dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute(
                "SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?",
                (limit,),
            )
            rows = await cur.fetchall()
            out = []
            for row in rows:
                data = dict(row)
                if data.get("result_json"):
                    data["result"] = json.loads(data["result_json"])
                if data.get("spec_json"):
                    data["spec"] = json.loads(data["spec_json"])
                out.append(data)
            return out
