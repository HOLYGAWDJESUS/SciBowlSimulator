from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import discord


def _truncate(s: str, max_len: int) -> str:
    s = s or ""
    return s if len(s) <= max_len else s[: max_len - 1] + "…"


def _safe_inline(s: str, max_len: int = 900) -> str:
    # Avoid breaking markdown (and embed limits)
    s = (s or "").replace("```", "ʼʼʼ")
    return _truncate(s, max_len)


@dataclass(frozen=True)
class EmbedWithFiles:
    embed: discord.Embed
    files: list[discord.File]


class EmbedFactory:
    """
    Pure UI layer.
    Builds embeds + attachments; does NOT touch DB, sessions, grading.
    """

    def __init__(self, *, footer_text: str = "SciBowlSimulator"):
        self.footer_text = footer_text

    def help_embed(self, generated_count: Optional[int] = None) -> EmbedWithFiles:
        embed = discord.Embed(
            title="",
            description=(
                "## **SciBowlSimulator Help**\n"
                "### **Commands**\n"
                "**-q <criteria(s)>**\n"
                "Posts a new question. If a question is already active in a channel, the old one is reposted. e.g. `-q phy hs mc` \n\n"

                "**-a <answer>**\n"
                "Answers the active question in the channel. e.g. `-a Boltzman's Constant` \n\n"

                "**-c**\n"
                "Reposts the active question in the channel. e.g. `-c`  \n\n"
                "**-help**\n"
                "Posts the help panel (you're seeing it right now). e.g. `-help`  \n\n"

                "### **Question Criteria**\n"

                "**Level**\n"
                "`hs` — High School\n"
                "`ms` — Middle School\n"
                "*(leave blank for both)*\n\n"

                "**Subject**\n"
                "`bio` `chem` `math` `phys` `es`\n"
                "*(leave blank for any type)*\n\n"

                "**Type**\n"
                "`mc` — Multiple Choice\n"
                "`sa` — Short Answer\n"
                "*(leave blank for both)*\n\n"

                "**Usage:**\n"
                " - You can include **multiple selections** (e.g. `bio chem`)\n"
                " - **Order does NOT matter** (`mc bio` = `bio mc`)\n"
                " - **Leaving a category blank includes all options**\n\n"

            ),
            color=discord.Color.blurple(),
        )
        footer = None
        if generated_count is not None:
            footer = f"Generated {generated_count} questions | made by @holygawdjesus"

        self._stamp(embed, footer=footer)
        return EmbedWithFiles(embed, [])

    def error_embed(self, message: str, *, title: str = "Error") -> EmbedWithFiles:
        embed = discord.Embed(
            title=title,
            description=_truncate(message, 2000),
            color=discord.Color.red(),
        )
        self._stamp(embed)
        return EmbedWithFiles(embed, [])

    def info_embed(self, message: str, *, title: str = "Info") -> EmbedWithFiles:
        embed = discord.Embed(
            title=title,
            description=_truncate(message, 2000),
            color=discord.Color.gold(),
        )
        self._stamp(embed)
        return EmbedWithFiles(embed, [])

    def balance_embed(
        self,
        *,
        user_display: str,
        user_id: int,
        points: int,
        avatar_url: Optional[str] = None,
        generated_count: Optional[int] = None
    ) -> EmbedWithFiles:
        embed = discord.Embed(
            title="SciBowlSimulator Points Bank",
            description=f"<@{user_id}> has earned **{points}** points in their lifetime! \n Answer more questions with `-q` and `-a` to earn more.",
            color=discord.Color.green(),
        )

        # Add user pfp
        if avatar_url:
            embed.set_thumbnail(url=avatar_url)

        footer = None
        if generated_count is not None:
            footer = f"Generated {generated_count} questions | made by @holygawdjesus"

        self._stamp(embed, footer=footer)
        return EmbedWithFiles(embed, [])
    def question_embed(
        self,
        question,
        *,
        is_repost: bool,
        criteria_text: Optional[str] = None,
        question_id: Optional[str] = None,
        generated_count: Optional[int] = None,
    ) -> EmbedWithFiles:
        title = "Science Bowl Question" if not is_repost else "Current Question (Repost)"
        embed = discord.Embed(title=title, color=discord.Color.blurple())

        if criteria_text:
            embed.description = f"Criteria: `{_truncate(criteria_text, 200)}`"

        embed.add_field(name="Category", value=str(getattr(question, "category", "UNKNOWN")), inline=True)
        embed.add_field(name="Level", value=str(getattr(question, "level", "UNKNOWN")), inline=True)
        embed.add_field(name="Type", value=str(getattr(question, "qtype", "UNKNOWN")), inline=True)

        files: list[discord.File] = []
        q_path = Path(getattr(question, "question_image_path", ""))
        if q_path.exists():
            files.append(discord.File(fp=str(q_path), filename="question.png"))
            embed.set_image(url="attachment://question.png")
        else:
            embed.add_field(name="Missing image", value=_safe_inline(str(q_path)), inline=False)

        footer = None
        if generated_count is not None:
            footer = f"Generated {generated_count} questions | made by @holygawdjesus"

        self._stamp(embed, footer=footer)
        return EmbedWithFiles(embed, files)

    def answer_result_embed(
        self,
        question,
        *,
        answerer_display: str,
        is_correct: bool,
        user_answer: str,
        expected_answer: str,
        points_delta: int,
        new_points_total: Optional[int],
        grade_reason: Optional[str] = None,
        expected_choice: Optional[str] = None,
        question_id: Optional[str] = None,
        generated_count: Optional[int] = None,
    ) -> EmbedWithFiles:
        title = "✅ Correct!" if is_correct else "❌ Incorrect"
        color = discord.Color.green() if is_correct else discord.Color.red()
        embed = discord.Embed(title=title, color=color)

        embed.add_field(name="Answerer", value=_truncate(answerer_display, 200), inline=False)
        embed.add_field(name="Your answer", value=f"`{_safe_inline(user_answer)}`", inline=False)
        embed.add_field(name="Official answer", value=f"`{_safe_inline(expected_answer)}`", inline=False)

        if expected_choice:
            embed.add_field(name="MC expected choice", value=f"`{expected_choice}`", inline=True)

        if grade_reason:
            embed.add_field(name="Grader reason", value=f"`{_safe_inline(grade_reason, 120)}`", inline=True)

        if is_correct:
            pts_line = f"+{points_delta} point"
            if new_points_total is not None:
                pts_line += f"New total: **{new_points_total} | **"
            embed.add_field(name="Points", value=pts_line, inline=False)

        files: list[discord.File] = []
        a_path = Path(getattr(question, "answer_image_path", ""))
        if a_path.exists():
            files.append(discord.File(fp=str(a_path), filename="answer.png"))
            embed.set_thumbnail(url="attachment://answer.png")

        footer = None
        if generated_count is not None:
            footer = f"Generated {generated_count} questions | made by @holygawdjesus"

        self._stamp(embed, footer=footer)
        return EmbedWithFiles(embed, files)

    def _stamp(self, embed: discord.Embed, *, footer: Optional[str] = None) -> None:
        embed.set_footer(text=footer or self.footer_text)
        embed.timestamp = discord.utils.utcnow()