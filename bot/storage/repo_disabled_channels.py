from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Set

import aiosqlite


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


async def ensure_schema(conn: aiosqlite.Connection) -> None:
    await conn.execute(
        '''
        CREATE TABLE IF NOT EXISTS disabled_channels (
        channel_id: TEXT PRIMARY KEY,
        disabled: INTEGER NOT NULL (0/1)
        updated_at: TEXT NOT NULL
        );
        '''
    )
    await conn.commit()


@dataclass(slots=True)
class DisabledChannelsRepo:
    '''Persistence for channel disabled/enabled state.'''
    conn: aiosqlite.Connection

    async def set_disabled(self, channel_id: int | str, disabled: bool = True) -> None:
        cid = str(channel_id)
        now = _utc_now_iso()
        val = 1 if disabled else 0

        await self.conn.execute(
            '''
            INSERT INTO disabled_channels (channel_id, disabled, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(channel_id) DO UPDATE SET
            disabled = excluded.disabled,
            updated_at = excluded.updated_at;
            ''',
            (cid, val, now),
        )
        await self.conn.commit()

    async def is_disabled(self, channel_id: int | str) -> bool:
        cid = str(channel_id)

        cur = await self.conn.execute(
            "SELECT disabled FROM disabled_channels WHERE channel_id = ?;",
            (cid,),
        )
        row = await cur.fetchone()
        await cur.close()

        return bool(int(row["disabled"])) if row else False

    async def list_disabled(self) -> Set[str]:
        '''Return a set of channel_ids that are disabled.'''
        cur = await self.conn.execute(
            "SELECT channel_id FROM disabled_channels WHERE disabled = 1;"
        )
        rows = await cur.fetchall()
        await cur.close()
        return {str(r["channel_id"]) for r in rows}

    async def remove(self, channel_id: int | str) -> None:
        '''Delete a row entirely (optional cleanup).'''
        cid = str(channel_id)
        await self.conn.execute("DELETE FROM disabled_channels WHERE channel_id = ?;", (cid,))
        await self.conn.commit()