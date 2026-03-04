from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Optional

from discord.ext import commands

from bot.services.criteria_interpreter import parse_criteria
from bot.services.answer_grader import grade_answer
from bot.session_manager.game_session import ChannelDisabledError, NoActiveQuestionError
from bot.services.questions_generator import NoQuestionsMatchError

from .embed_factory import EmbedFactory


@dataclass(frozen=True)
class PublicServices:
    session_manager: object

    # Storage repos
    player_points_repo: object
    bot_stats_repo: object
    disabled_channels_repo: object
    question_stats_repo: object

    # UI
    embed_factory: EmbedFactory
    channel_locks: dict[int, asyncio.Lock]

    # Constants
    total_questions_key: str
    make_question_id: callable  # make_question_id(question) -> str


class PublicCommands(commands.Cog):
    """
    Public commands:
      -q [criteria] or -q for no criteria
      -a <answer>
      -c
      -balance [@user|id] or -balance for self balance
      -help
    """

    def __init__(self, bot: commands.Bot, services: PublicServices):
        self.bot = bot
        self.s = services

    @commands.command(name="help")
    async def help_cmd(self, ctx: commands.Context) -> None:
        out = self.s.embed_factory.help_embed()
        await ctx.send(embed=out.embed, files=out.files)

    @commands.command(name="balance")
    async def balance_cmd(self, ctx: commands.Context, *, target: Optional[str] = None) -> None:
        user = await self._resolve_user(ctx, target)
        if user is None:
            out = self.s.embed_factory.error_embed("Could not resolve that user. Use a mention or a numeric ID. \n For example: -balance @user")
            await ctx.send(embed=out.embed)
            return

        points = await self.s.player_points_repo.get_points(user.id)
        out = self.s.embed_factory.balance_embed(user_display=str(user), user_id=user.id, points=points)
        await ctx.send(embed=out.embed)

    @commands.command(name="c")
    async def repost_cmd(self, ctx: commands.Context) -> None:
        if await self._blocked(ctx):
            return

        q = self._get_active_question(ctx.channel.id)
        if q is None:
            out = self.s.embed_factory.error_embed("No active question in this channel. Use `-q` to start a new one.")
            await ctx.send(embed=out.embed)
            return

        qid = self.s.make_question_id(q)
        out = self.s.embed_factory.question_embed(q, is_repost=True, question_id=qid)
        await ctx.send(embed=out.embed, files=out.files)

    @commands.command(name="q")
    async def question_cmd(self, ctx: commands.Context, *, criteria: Optional[str] = None) -> None:
        if await self._blocked(ctx):
            return

        # -q sends an error message but also repeats the current question
        q_active = self._get_active_question(ctx.channel.id)
        if q_active is not None:
            out_err = self.s.embed_factory.error_embed(
                "A question is already active in this channel. Reposting it.\n"
                "Use `-a <answer>` to answer, or `-c` to repost without this warning.",
                title="⚠️ Active question",
            )
            await ctx.send(embed=out_err.embed)

            qid = self.s.make_question_id(q_active)
            out_q = self.s.embed_factory.question_embed(q_active, is_repost=True, criteria_text=criteria, question_id=qid)
            await ctx.send(embed=out_q.embed, files=out_q.files)
            return

        # No active question: parse criteria if provided
        criteria_text = (criteria or "").strip()
        picker_kwargs = {}
        if criteria_text:
            parsed = parse_criteria(criteria_text)
            if not parsed.accepted:
                out = self.s.embed_factory.error_embed(
                    f"Unknown/invalid criteria token(s): {', '.join(parsed.unknown_token_list)}",
                    title="⚠️ Criteria Error",
                )
                await ctx.send(embed=out.embed)
                return
            picker_kwargs = dict(parsed.picker)

        # Generate/start question in session manager
        try:
            q = self.s.session_manager.handle_question(ctx.channel.id, **picker_kwargs)
        except ChannelDisabledError:
            out = self.s.embed_factory.error_embed("This channel is disabled for the bot.")
            await ctx.send(embed=out.embed)
            return
        except NoQuestionsMatchError:
            out = self.s.embed_factory.error_embed(
                "No questions match that criteria. Try fewer filters (example: `-q hs bio`)."
            )
            await ctx.send(embed=out.embed)
            return
        except Exception as e:
            out = self.s.embed_factory.error_embed(f"Failed to start a question: {type(e).__name__}: {e}")
            await ctx.send(embed=out.embed)
            return

        # New question was actually generated -> increment counter
        try:
            await self.s.bot_stats_repo.increment_int(self.s.total_questions_key, 1)
        except Exception:
            pass

        qid = self.s.make_question_id(q)
        out_q = self.s.embed_factory.question_embed(q, is_repost=False, criteria_text=criteria_text or None, question_id=qid)
        msg = await ctx.send(embed=out_q.embed, files=out_q.files)

        # Store message id in the session manager
        try:
            self.s.session_manager.set_message_id(ctx.channel.id, msg.id)
        except Exception:
            pass


    # Add bonus question to follow up after this.
    @commands.command(name="a")
    async def answer_cmd(self, ctx: commands.Context, *, answer: Optional[str] = None) -> None:
        if await self._blocked(ctx):
            return

        ans = (answer or "").strip()
        if not ans:
            out = self.s.embed_factory.error_embed("Usage: `-a <answer>`")
            await ctx.send(embed=out.embed)
            return

        lock = self.s.channel_locks.setdefault(ctx.channel.id, asyncio.Lock())
        async with lock:
            # End question immediately + get question
            try:
                q = self.s.session_manager.handle_answer(ctx.channel.id)
            except ChannelDisabledError:
                out = self.s.embed_factory.error_embed("This channel is disabled for the bot.")
                await ctx.send(embed=out.embed)
                return
            except NoActiveQuestionError:
                out = self.s.embed_factory.error_embed("No active question. Use `-q` first.")
                await ctx.send(embed=out.embed)
                return
            except Exception as e:
                out = self.s.embed_factory.error_embed(f"Failed to accept answer: {type(e).__name__}: {e}")
                await ctx.send(embed=out.embed)
                return

            # Grade using services.answer_grader
            gr = grade_answer(getattr(q, "qtype", ""), getattr(q, "parsed_answer", ""), ans)
            is_correct = bool(getattr(gr, "is_correct", False))

            qid = self.s.make_question_id(q)

            # Record attempt/correct for solve-rate tracking
            try:
                await self.s.question_stats_repo.record_attempt(qid, correct=is_correct)
            except Exception:
                pass

            # Award points if correct
            points_delta = 0
            new_total: Optional[int] = None
            if is_correct:
                points_delta = 1
                try:
                    new_total = await self.s.player_points_repo.add_points(ctx.author.id, 1)
                except Exception:
                    new_total = None

            out = self.s.embed_factory.answer_result_embed(
                q,
                answerer_display=str(ctx.author),
                is_correct=is_correct,
                user_answer=ans,
                expected_answer=getattr(q, "parsed_answer", ""),
                points_delta=points_delta,
                new_points_total=new_total,
                grade_reason=getattr(gr, "reason", None),
                expected_choice=getattr(gr, "expected_choice", None),
                question_id=qid,
            )
            await ctx.send(embed=out.embed, files=out.files)

    ##########
    # Helpers
    ##########

    async def _blocked(self, ctx: commands.Context) -> bool:
        """
        Check DB-backed disabled_channels first.
        (SessionManager also checks its in-memory set, but DB is source of truth.)
        """
        try:
            if await self.s.disabled_channels_repo.is_disabled(ctx.channel.id):
                out = self.s.embed_factory.error_embed("This channel is disabled for the bot.")
                await ctx.send(embed=out.embed)
                return True
        except Exception:
            # If DB check fails, do not block usage but let SessionManager raise if needed.
            return False
        return False

    def _get_active_question(self, channel_id: int):
        sm = self.s.session_manager
        try:
            sess = sm.get_session(channel_id)
            return getattr(sess, "question", None)
        except Exception:
            return None

    async def _resolve_user(self, ctx: commands.Context, raw: Optional[str]):
        if raw is None or not raw.strip():
            return ctx.author

        if getattr(ctx.message, "mentions", None) and ctx.message.mentions:
            return ctx.message.mentions[0]

        raw = raw.strip()
        if raw.isdigit():
            try:
                return await self.bot.fetch_user(int(raw))
            except Exception:
                return None

        return None