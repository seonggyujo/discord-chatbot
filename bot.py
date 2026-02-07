"""디스코드 AI 챗봇 - 진입점"""

from __future__ import annotations

import asyncio

import discord  # type: ignore
from discord.ext import commands  # type: ignore

from core.config import DISCORD_TOKEN, GROQ_API_KEY, logger

# 봇 설정
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready() -> None:
    """봇 준비 완료."""
    logger.info("%s 봇이 시작되었습니다!", bot.user)
    logger.info("서버 %d개에 연결됨", len(bot.guilds))


@bot.event
async def on_message(message: discord.Message) -> None:
    """메시지 이벤트 처리 - 봇 메시지 필터링 후 명령어 처리."""
    if message.author.bot:
        return
    await bot.process_commands(message)


async def main() -> None:
    """봇을 시작합니다."""
    if not DISCORD_TOKEN:
        logger.error("DISCORD_BOT_TOKEN이 설정되지 않았습니다.")
        return
    if not GROQ_API_KEY:
        logger.error("GROQ_API_KEY가 설정되지 않았습니다.")
        return

    async with bot:
        await bot.load_extension("cogs.chat")
        await bot.load_extension("cogs.info")
        await bot.start(DISCORD_TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
