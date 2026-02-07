"""봇 정보 명령어 Cog"""

from __future__ import annotations

from discord.ext import commands  # type: ignore

from core.config import MODEL


class InfoCog(commands.Cog):
    """봇 정보를 표시하는 Cog."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.command(name="info")
    async def info_command(self, ctx: commands.Context) -> None:
        """봇 정보 표시."""
        info_text = f"""**[봇 정보]**
모델: {MODEL}
API: Groq (무료 티어)
개발자: seonggyujo
이메일: whtjdrb020@gmail.com
GitHub: https://github.com/seonggyujo/discord-chatbot"""
        await ctx.reply(info_text)


async def setup(bot: commands.Bot) -> None:
    """Cog을 봇에 등록합니다."""
    await bot.add_cog(InfoCog(bot))
