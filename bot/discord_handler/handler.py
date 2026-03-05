from __future__ import annotations
from pathlib import Path
import asyncio
import os

import discord
from discord.ext import commands

from bot.question_base.questions_repo import QuestionRepository
from bot.services.questions_generator import QuestionPicker
from bot.session_manager.game_session import SessionManager

from bot.storage.db import Database, DatabaseConfig
from bot.storage.repo_player_points import PlayerPointsRepo
from bot.storage.repo_disabled_channels import DisabledChannelsRepo
from bot.storage.repo_bot_stats import BotStatsRepo, TOTAL_QUESTIONS_GENERATED
from bot.storage.repo_questions_stats import QuestionStatsRepo, make_question_id

from .embed_factory import EmbedFactory
from .public_commands import PublicCommands, PublicServices


class SciBowlBot(commands.Bot):
    """
    Creates the shared DB connection + repos, loads questions, wires SessionManager,
    and registers the public commands cog.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.db: Database | None = None

    async def setup_hook(self) -> None:
        # ---- DB init ----
        db_path = Path(os.getenv("SCIBOWL_DB_PATH", "bot/storage/data.sqlite"))
        self.db = Database(DatabaseConfig(db_path=db_path))
        await self.db.connect()
        await self.db.init_schema()

        # ---- Repos ----
        player_points_repo = PlayerPointsRepo(self.db.conn)
        disabled_channels_repo = DisabledChannelsRepo(self.db.conn)
        bot_stats_repo = BotStatsRepo(self.db.conn)
        question_stats_repo = QuestionStatsRepo(self.db.conn)

        # ---- Question repo + picker ----
        qrepo = QuestionRepository()
        picker = QuestionPicker(qrepo.get_all_questions())

        # ---- Session manager (session-only: start/repost/end) ----
        session_manager = SessionManager(picker)

        # Load disabled channels from DB into SessionManager's in-memory set
        try:
            disabled = await disabled_channels_repo.list_disabled()
            session_manager.disabled_channels = set(disabled)
        except Exception:
            pass

        # ---- UI factory ----
        embed_factory = EmbedFactory()

        services = PublicServices(
            session_manager=session_manager,
            player_points_repo=player_points_repo,
            bot_stats_repo=bot_stats_repo,
            disabled_channels_repo=disabled_channels_repo,
            question_stats_repo=question_stats_repo,
            embed_factory=embed_factory,
            channel_locks={},
            total_questions_key=TOTAL_QUESTIONS_GENERATED,
            make_question_id=make_question_id,
        )

        await self.add_cog(PublicCommands(self, services))

    async def close(self) -> None:
        try:
            if self.db is not None:
                await self.db.close()
        finally:
            await super().close()


def build_bot() -> SciBowlBot:
    intents = discord.Intents.default()
    intents.message_content = True  # required for prefix commands
    intents.members = True

    return SciBowlBot(
        command_prefix="-",
        intents=intents,
        allowed_mentions=discord.AllowedMentions(users=True, roles=False, everyone=False),
        help_command=None,  # I implement -help myself
    )