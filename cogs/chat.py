"""채팅 관련 명령어 및 이벤트 Cog"""

from __future__ import annotations

from collections import defaultdict, deque
from time import time

import discord  # type: ignore
from discord.ext import commands, tasks  # type: ignore

from core.api import GroqClient
from core.config import (
    COOLDOWN_SECONDS,
    MAX_CONTEXT,
    MAX_MESSAGE_LENGTH,
    SYSTEM_PROMPT,
    logger,
)
from core.filters import check_blocked


class ChatCog(commands.Cog):
    """AI 채팅 기능을 담당하는 Cog.

    - 멘션(@봇) 및 !chat 명령어로 AI 대화
    - 채널별 대화 컨텍스트 유지 (최근 10개)
    - 채널별 쿨타임 (3초)
    - 비활성 채널 자동 정리 (1시간)
    """

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.api = GroqClient()
        self.conversation_history: defaultdict[int, deque[dict[str, str]]] = (
            defaultdict(lambda: deque(maxlen=MAX_CONTEXT))
        )
        self.last_request_time: defaultdict[int, float] = defaultdict(float)

    async def cog_load(self) -> None:
        """Cog 로드 시 호출 - API 세션 시작 및 정리 태스크 시작"""
        await self.api.start()
        self.cleanup_inactive.start()

    async def cog_unload(self) -> None:
        """Cog 언로드 시 호출 - 리소스 정리"""
        self.cleanup_inactive.cancel()
        await self.api.close()

    # --- 유틸리티 ---

    def check_cooldown(self, channel_id: int) -> tuple[bool, float]:
        """쿨타임 확인. (통과여부, 남은시간) 반환."""
        current_time = time()
        elapsed = current_time - self.last_request_time[channel_id]

        if elapsed < COOLDOWN_SECONDS:
            return False, COOLDOWN_SECONDS - elapsed

        self.last_request_time[channel_id] = current_time
        return True, 0.0

    @staticmethod
    def split_message(
        text: str, max_length: int = MAX_MESSAGE_LENGTH
    ) -> list[str]:
        """긴 메시지를 Discord 제한(2000자)에 맞게 분할."""
        if len(text) <= max_length:
            return [text]

        chunks: list[str] = []
        while text:
            if len(text) <= max_length:
                chunks.append(text)
                break

            # 줄바꿈 또는 공백에서 분할
            split_index = text.rfind("\n", 0, max_length)
            if split_index == -1:
                split_index = text.rfind(" ", 0, max_length)
            if split_index == -1:
                split_index = max_length

            chunks.append(text[:split_index])
            text = text[split_index:].lstrip()

        return chunks

    # --- 핵심 로직 ---

    async def process_message(
        self, message: discord.Message, content: str
    ) -> None:
        """공통 메시지 처리 로직."""
        channel_id = message.channel.id

        # 쿨타임 체크
        can_proceed, remaining = self.check_cooldown(channel_id)
        if not can_proceed:
            await message.reply(
                f"잠시만요! {remaining:.1f}초 후에 다시 시도해주세요."
            )
            return

        # 키워드 필터 체크 (API 호출 전 차단)
        blocked_response = check_blocked(content)
        if blocked_response:
            await message.reply(blocked_response)
            return

        # 컨텍스트에 메시지 추가
        self.conversation_history[channel_id].append(
            {"role": "user", "content": content}
        )

        # API 요청 메시지 구성
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            *list(self.conversation_history[channel_id]),
        ]

        # API 호출 (입력 중 표시)
        async with message.channel.typing():
            response, error = await self.api.chat(messages)

        if error:
            # 실패 시 컨텍스트에서 제거
            self.conversation_history[channel_id].pop()
            await message.reply(error)
            return

        # 성공 시 어시스턴트 응답도 컨텍스트에 저장
        self.conversation_history[channel_id].append(
            {"role": "assistant", "content": response}
        )

        # 메시지 분할 전송
        chunks = self.split_message(response)
        for i, chunk in enumerate(chunks):
            if i == 0:
                await message.reply(chunk)
            else:
                await message.channel.send(chunk)

    # --- 이벤트 리스너 ---

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """멘션(@봇) 기반 메시지 처리."""
        if message.author.bot:
            return

        if not self.bot.user.mentioned_in(message):
            return

        # @everyone, @here 멘션 제외
        if message.mention_everyone:
            return

        content = (
            message.content.replace(f"<@{self.bot.user.id}>", "")
            .replace(f"<@!{self.bot.user.id}>", "")
            .strip()
        )

        if content:
            await self.process_message(message, content)
        else:
            await message.reply(
                "메시지를 입력해주세요! 예: `@봇이름 안녕하세요`"
            )

    # --- 명령어 ---

    @commands.command(name="chat")
    async def chat_command(
        self, ctx: commands.Context, *, message: str = ""
    ) -> None:
        """AI와 대화하는 명령어. 사용법: !chat <메시지>"""
        if not message:
            await ctx.reply("메시지를 입력해주세요! 예: `!chat 안녕하세요`")
            return
        await self.process_message(ctx.message, message)

    # --- 주기적 태스크 ---

    @tasks.loop(hours=1)
    async def cleanup_inactive(self) -> None:
        """1시간 이상 비활성 채널의 대화 데이터를 정리합니다."""
        current = time()
        inactive = [
            ch_id
            for ch_id, last_time in self.last_request_time.items()
            if current - last_time > 3600
        ]
        for ch_id in inactive:
            self.conversation_history.pop(ch_id, None)
            self.last_request_time.pop(ch_id, None)
        if inactive:
            logger.info("비활성 채널 %d개 정리 완료", len(inactive))

    @cleanup_inactive.before_loop
    async def before_cleanup(self) -> None:
        """봇이 준비될 때까지 정리 태스크 대기."""
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot) -> None:
    """Cog을 봇에 등록합니다."""
    await bot.add_cog(ChatCog(bot))
