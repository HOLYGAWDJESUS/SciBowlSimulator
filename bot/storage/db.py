from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import aiosqlite


@dataclass(slots=True)
class DatabaseConfig:
    '''
    Config for the SQLite database connection
    '''
    db_path: Path
    pragmas_wal: bool = True
    busy_timeout_ms: int = 5000  # avoid database is locked spike


class Database:
    '''
    a single shared aiosqlite connection.
    usage:
    db = Database(DatabaseConfig(Path("bot/storage/data.sqlite")))
    await db.connect()
    await db.init_schema()
    pass db.conn into repos
    await db.close()
    '''

    def __init__(self, config: DatabaseConfig):
        self.config = config
        self._conn: Optional[aiosqlite.Connection] = None

    @property
    def conn(self) -> aiosqlite.Connection:
        if self._conn is None:
            raise RuntimeError("Database not connected; Try call all await db.connect() first.")
        return self._conn

    async def connect(self) -> aiosqlite.Connection:
        '''Open the SQLite connection and apply recommended pragmas.'''
        # Ensure folder exists
        self.config.db_path.parent.mkdir(parents=True, exist_ok=True)

        conn = await aiosqlite.connect(self.config.db_path.as_posix())
        # Fetch rows like dict-ish access by column name
        conn.row_factory = aiosqlite.Row

        # PRAGMAs
        await conn.execute("PRAGMA foreign_keys = ON;")
        await conn.execute(f"PRAGMA busy_timeout = {int(self.config.busy_timeout_ms)};")

        if self.config.pragmas_wal:
            # WAL is better for concurrent reads/writes typical of bots
            await conn.execute("PRAGMA journal_mode = WAL;")
            await conn.execute("PRAGMA synchronous = NORMAL;")

        await conn.commit()
        self._conn = conn
        return conn

    async def init_schema(self) -> None:
        '''
        Create tables if don't exist.
        Each repo owns its own ensure_schema() so schema stays near code.
        '''
        from .repo_player_points import ensure_schema as ensure_points
        from .repo_disabled_channels import ensure_schema as ensure_channels
        from .repo_bot_stats import ensure_schema as ensure_stats
        from .repo_questions_stats import ensure_schema as ensure_qstats

        await ensure_points(self.conn)
        await ensure_channels(self.conn)
        await ensure_stats(self.conn)
        await ensure_qstats(self.conn)

    async def close(self) -> None:
        '''Close the connection.'''
        if self._conn is not None:
            await self._conn.close()
            self._conn = None