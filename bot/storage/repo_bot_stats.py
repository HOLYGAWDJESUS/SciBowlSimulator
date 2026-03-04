from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict

import aiosqlite


# Common keys (add more as needed)
TOTAL_QUESTIONS_GENERATED = "total_questions_generated"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


async def ensure_schema(conn: aiosqlite.Connection) -> None:
    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS bot_stats (
            key        TEXT PRIMARY KEY,
            value      INTEGER NOT NULL,
            updated_at TEXT NOT NULL
        );
        """
    )
    await conn.commit()


@dataclass(slots=True)
class BotStatsRepo:
    """Key-value integer stats for the bot (global counters)."""
    conn: aiosqlite.Connection

    async def get_int(self, key: str, default: int = 0) -> int:
        cur = await self.conn.execute("SELECT value FROM bot_stats WHERE key = ?;", (key,))
        row = await cur.fetchone()
        await cur.close()
        return int(row["value"]) if row else int(default)

    async def set_int(self, key: str, value: int) -> None:
        now = _utc_now_iso()
        await self.conn.execute(
            """
            INSERT INTO bot_stats (key, value, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                updated_at = excluded.updated_at;
            """,
            (key, int(value), now),
        )
        await self.conn.commit()

    async def increment_int(self, key: str, delta: int = 1) -> int:
        """
        Atomically increment a counter and return the new value.
        """
        now = _utc_now_iso()
        await self.conn.execute(
            """
            INSERT INTO bot_stats (key, value, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                value = bot_stats.value + excluded.value,
                updated_at = excluded.updated_at;
            """,
            (key, int(delta), now),
        )
        await self.conn.commit()
        return await self.get_int(key, default=0)

    async def get_all(self) -> Dict[str, int]:
        cur = await self.conn.execute("SELECT key, value FROM bot_stats;")
        rows = await cur.fetchall()
        await cur.close()
        return {str(r["key"]): int(r["value"]) for r in rows}