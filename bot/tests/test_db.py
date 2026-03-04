import asyncio
from pathlib import Path

from bot.storage.db import Database, DatabaseConfig
from bot.storage.repo_player_points import PlayerPointsRepo
from bot.storage.repo_disabled_channels import DisabledChannelsRepo
from bot.storage.repo_bot_stats import BotStatsRepo, TOTAL_QUESTIONS_GENERATED
from bot.storage.repo_questions_stats import QuestionStatsRepo


async def run_storage_smoke_test() -> None:
    print(">>> test_db.py started")

    # Put the test DB next to your real DB (but separate file)
    test_db_path = Path("bot/storage/data_test.sqlite").resolve()

    # Start fresh each run
    if test_db_path.exists():
        test_db_path.unlink()

    print(f"[TEST] Using DB file: {test_db_path}")

    db = Database(DatabaseConfig(db_path=test_db_path))
    await db.connect()
    await db.init_schema()

    points_repo = PlayerPointsRepo(db.conn)
    stats_repo = BotStatsRepo(db.conn)
    disabled_repo = DisabledChannelsRepo(db.conn)
    qstats_repo = QuestionStatsRepo(db.conn)

    # 1) bot_stats
    print("[TEST] bot_stats increment...")
    v1 = await stats_repo.increment_int(TOTAL_QUESTIONS_GENERATED, 1)
    v2 = await stats_repo.increment_int(TOTAL_QUESTIONS_GENERATED, 3)
    assert v2 == v1 + 3
    print(f"  total_questions_generated = {v2}")

    # 2) disabled channels
    print("[TEST] disabled_channels set/list/is_disabled...")
    channel_a = "123"
    channel_b = "456"
    assert await disabled_repo.is_disabled(channel_a) is False
    await disabled_repo.set_disabled(channel_a, True)
    await disabled_repo.set_disabled(channel_b, True)
    disabled = await disabled_repo.list_disabled()
    print(f"  disabled = {sorted(disabled)}")
    assert channel_a in disabled and channel_b in disabled

    await disabled_repo.set_disabled(channel_b, False)
    disabled2 = await disabled_repo.list_disabled()
    print(f"  disabled after enabling one = {sorted(disabled2)}")
    assert channel_a in disabled2 and channel_b not in disabled2

    # 3) global player points
    print("[TEST] player_points add/get/leaderboard...")
    user_1 = "111"
    user_2 = "222"
    assert await points_repo.get_points(user_1) == 0
    p2 = await points_repo.add_points(user_1, 5)
    await points_repo.add_points(user_2, 2)
    lb = await points_repo.leaderboard(10)
    print(f"  leaderboard = {lb}")
    assert p2 == 5

    # 4) question stats
    print("[TEST] question_stats record_attempt/get_stats...")
    qid = "q:test_set|hs|round1|1|sa|physics|tossup"
    await qstats_repo.record_attempt(qid, correct=False)
    await qstats_repo.record_attempt(qid, correct=True)
    attempts, correct, rate = await qstats_repo.get_stats(qid)
    print(f"  {qid}: attempts={attempts}, correct={correct}, rate={rate:.3f}")
    assert attempts == 2 and correct == 1

    await db.close()

    # 5) persistence check (reopen)
    print("[TEST] persistence after reopen...")
    db2 = Database(DatabaseConfig(db_path=test_db_path))
    await db2.connect()
    await db2.init_schema()

    stats_repo2 = BotStatsRepo(db2.conn)
    points_repo2 = PlayerPointsRepo(db2.conn)

    v_after = await stats_repo2.get_int(TOTAL_QUESTIONS_GENERATED)
    p_after = await points_repo2.get_points(user_1)
    print(f"  after reopen: total_questions_generated={v_after}, user_1_points={p_after}")
    assert v_after == v2 and p_after == 5

    await db2.close()

    print("All DB tests passed.")


def main() -> None:
    asyncio.run(run_storage_smoke_test())


if __name__ == "__main__":
    main()