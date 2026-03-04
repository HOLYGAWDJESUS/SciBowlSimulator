from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Tuple

import aiosqlite


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


async def ensure_schema(conn: aiosqlite.Connection) -> None:
    """
    Global points table: points are shared across all guilds.
    Primary key is only user_id.
    """
    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS player_points (
            user_id    TEXT PRIMARY KEY,
            points     INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT NOT NULL
        );
        """
    )
    await conn.commit()


@dataclass(slots=True)
class PlayerPointsRepo:
    """Persistence for global per-player points."""
    conn: aiosqlite.Connection

    async def get_points(self, user_id: int | str) -> int:
        uid = str(user_id)

        cur = await self.conn.execute(
            "SELECT points FROM player_points WHERE user_id = ?;",
            (uid,),
        )
        row = await cur.fetchone()
        await cur.close()
        return int(row["points"]) if row else 0

    async def add_points(self, user_id: int | str, delta: int = 1) -> int:
        """
        Atomically add points (delta can be negative).
        Returns the new total.
        """
        uid = str(user_id)
        now = _utc_now_iso()

        await self.conn.execute(
            """
            INSERT INTO player_points (user_id, points, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                points = player_points.points + excluded.points,
                updated_at = excluded.updated_at;
            """,
            (uid, int(delta), now),
        )
        await self.conn.commit()
        return await self.get_points(uid)

    async def set_points(self, user_id: int | str, points: int) -> None:
        """Set an absolute points value (admin/debug)."""
        uid = str(user_id)
        now = _utc_now_iso()

        await self.conn.execute(
            """
            INSERT INTO player_points (user_id, points, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                points = excluded.points,
                updated_at = excluded.updated_at;
            """,
            (uid, int(points), now),
        )
        await self.conn.commit()

    async def leaderboard(self, limit: int = 10) -> List[Tuple[str, int]]:
        """Return [(user_id, points), ...] sorted by points desc (global leaderboard)."""
        lim = max(1, int(limit))

        cur = await self.conn.execute(
            """
            SELECT user_id, points
            FROM player_points
            ORDER BY points DESC, user_id ASC
            LIMIT ?;
            """,
            (lim,),
        )
        rows = await cur.fetchall()
        await cur.close()

        return [(str(r["user_id"]), int(r["points"])) for r in rows]