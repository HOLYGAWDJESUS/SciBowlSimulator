from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable, Optional, Protocol, Tuple, List
import re

import aiosqlite


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _norm_token(s: str) -> str:
    """
    Normalize tokens into stable, filesystem-safe-ish identifiers:
    - lower
    - non-alnum -> underscores
    - trim underscores
    """
    s = s.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_") or "x"


class QuestionLike(Protocol):
    """
    Minimal protocol for your Question dataclass/object.
    This avoids importing your Question type and creating circular imports.
    """
    set_name: str
    level: str
    bonus: bool
    round_name: str
    num: int
    category: str
    qtype: str



def make_question_id_from_fields(
    *,
    set_name: str,
    level: str,
    round_name: str,
    num: int,
    qtype: str,
    category: str,
    bonus: bool,
    extra: Optional[str] = None,
) -> str:
    """
    Deterministic ID. Same question => same question_id across restarts.
    Human-readable and stable.
    """
    parts = [
        _norm_token(set_name),
        _norm_token(level),
        _norm_token(round_name),
        str(int(num)),
        _norm_token(qtype),
        _norm_token(category),
        "bonus" if bonus else "tossup",
    ]
    if extra:
        parts.append(_norm_token(extra))
    return "q:" + "|".join(parts)


def make_question_id(q: QuestionLike) -> str:
    """
    Create a deterministic question_id from a Question-like object.
    """
    return make_question_id_from_fields(
        set_name=q.set_name,
        level=q.level,
        round_name=q.round_name,
        num=q.num,
        qtype=q.qtype,
        category=q.category,
        bonus=bool(q.bonus),
    )


async def ensure_schema(conn: aiosqlite.Connection) -> None:
    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS question_stats (
            question_id  TEXT PRIMARY KEY,
            attempts     INTEGER NOT NULL DEFAULT 0,
            correct      INTEGER NOT NULL DEFAULT 0,
            last_seen_at TEXT NOT NULL
        );
        """
    )
    await conn.commit()


@dataclass(slots=True)
class QuestionStatsRepo:
    """Track attempts/correct counts per deterministic question_id."""
    conn: aiosqlite.Connection

    async def record_attempt(self, question_id: str, correct: bool) -> None:
        """
        Record one attempt for this question.
        If correct=True, also increments correct count.
        Atomic single-statement UPSERT.
        """
        now = _utc_now_iso()
        add_correct = 1 if correct else 0

        await self.conn.execute(
            """
            INSERT INTO question_stats (question_id, attempts, correct, last_seen_at)
            VALUES (?, 1, ?, ?)
            ON CONFLICT(question_id) DO UPDATE SET
                attempts = question_stats.attempts + 1,
                correct = question_stats.correct + excluded.correct,
                last_seen_at = excluded.last_seen_at;
            """,
            (question_id, add_correct, now),
        )
        await self.conn.commit()

    async def get_stats(self, question_id: str) -> Tuple[int, int, float]:
        """
        Returns (attempts, correct, rate).
        rate is 0.0 if attempts == 0.
        """
        cur = await self.conn.execute(
            "SELECT attempts, correct FROM question_stats WHERE question_id = ?;",
            (question_id,),
        )
        row = await cur.fetchone()
        await cur.close()

        if not row:
            return 0, 0, 0.0

        attempts = int(row["attempts"])
        correct = int(row["correct"])
        rate = (correct / attempts) if attempts > 0 else 0.0
        return attempts, correct, rate

    async def hardest(self, min_attempts: int = 10, limit: int = 10) -> List[Tuple[str, int, int, float]]:
        """
        Returns a list of (question_id, attempts, correct, rate) for questions with
        lowest success rate, with a minimum attempts threshold.
        """
        min_a = max(1, int(min_attempts))
        lim = max(1, int(limit))

        cur = await self.conn.execute(
            """
            SELECT question_id, attempts, correct
            FROM question_stats
            WHERE attempts >= ?
            ORDER BY (CAST(correct AS REAL) / CAST(attempts AS REAL)) ASC,
                     attempts DESC
            LIMIT ?;
            """,
            (min_a, lim),
        )
        rows = await cur.fetchall()
        await cur.close()

        out: List[Tuple[str, int, int, float]] = []
        for r in rows:
            qid = str(r["question_id"])
            attempts = int(r["attempts"])
            correct = int(r["correct"])
            rate = (correct / attempts) if attempts > 0 else 0.0
            out.append((qid, attempts, correct, rate))
        return out