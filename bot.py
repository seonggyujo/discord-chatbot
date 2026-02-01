import os
from collections import defaultdict, deque
from time import time

import discord  # type: ignore
from discord.ext import commands  # type: ignore
import aiohttp  # type: ignore
from dotenv import load_dotenv  # type: ignore

# 환경변수 로드
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# 설정
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "openai/gpt-oss-120b"
SYSTEM_PROMPT = """너는 디스코드 챗봇이야.
질문에 대한 답변만 해. 핵심만 짧게 말해.
최대 300자 이내로 답변해.
되묻는 질문 하지마.
불필요한 인사말이나 부연설명 생략해.
한국어로 대답해."""

MAX_CONTEXT = 5
COOLDOWN_SECONDS = 3
MAX_MESSAGE_LENGTH = 2000

# 금지 키워드 (API 호출 전 차단)
BLOCKED_KEYWORDS = ["해마 이모지", "seahorse emoji", "해마이모지", "해마 emoji"]
BLOCKED_RESPONSE = "표준 유니코드 목록에 존재하지 않습니다."

# 상태 저장 (메모리)
conversation_history = defaultdict(lambda: deque(maxlen=MAX_CONTEXT))
last_request_time = defaultdict(float)

# 봇 설정
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)


def check_cooldown(channel_id: int) -> tuple:
    """쿨타임 확인, (통과여부, 남은시간) 반환"""
    current_time = time()
    elapsed = current_time - last_request_time[channel_id]
    
    if elapsed < COOLDOWN_SECONDS:
        return False, COOLDOWN_SECONDS - elapsed
    
    last_request_time[channel_id] = current_time
    return True, 0


def split_message(text: str, max_length: int = MAX_MESSAGE_LENGTH) -> list:
    """긴 메시지를 분할"""
    if len(text) <= max_length:
        return [text]
    
    chunks = []
    while text:
        if len(text) <= max_length:
            chunks.append(text)
            break
        
        # 줄바꿈 또는 공백에서 분할
        split_index = text.rfind('\n', 0, max_length)
        if split_index == -1:
            split_index = text.rfind(' ', 0, max_length)
        if split_index == -1:
            split_index = max_length
        
        chunks.append(text[:split_index])
        text = text[split_index:].lstrip()
    
    return chunks


async def call_groq_api(channel_id: int, user_message: str) -> str:
    """Groq API 호출 및 응답 반환"""
    # 금지된 키워드 체크
    message_lower = user_message.lower()
    for keyword in BLOCKED_KEYWORDS:
        if keyword in message_lower:
            return BLOCKED_RESPONSE
    
    # 컨텍스트에 현재 메시지 추가
    conversation_history[channel_id].append({
        "role": "user",
        "content": user_message
    })
    
    # API 요청 메시지 구성
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        *list(conversation_history[channel_id])
    ]
    
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": MODEL,
        "messages": messages,
        "max_tokens": 512,
        "temperature": 0.7
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(GROQ_API_URL, headers=headers, json=payload) as resp:
                if resp.status == 429:
                    # 실패 시 컨텍스트에서 제거
                    conversation_history[channel_id].pop()
                    return "API 요청 한도를 초과했습니다. 잠시 후 다시 시도해주세요."
                
                if resp.status != 200:
                    # 실패 시 컨텍스트에서 제거
                    conversation_history[channel_id].pop()
                    return f"API 오류가 발생했습니다. (상태 코드: {resp.status})"
                
                data = await resp.json()
                assistant_message = data["choices"][0]["message"]["content"]
                
                # 어시스턴트 응답도 컨텍스트에 저장
                conversation_history[channel_id].append({
                    "role": "assistant",
                    "content": assistant_message
                })
                
                return assistant_message
                
    except aiohttp.ClientError as e:
        # 실패 시 컨텍스트에서 제거
        conversation_history[channel_id].pop()
        print(f"API 연결 오류: {e}")
        return "API 연결 오류가 발생했습니다. 잠시 후 다시 시도해주세요."
    except Exception as e:
        # 실패 시 컨텍스트에서 제거
        conversation_history[channel_id].pop()
        print(f"예외 발생: {e}")
        return "오류가 발생했습니다. 잠시 후 다시 시도해주세요."


async def process_message(message, content: str):
    """공통 메시지 처리 로직"""
    channel_id = message.channel.id
    
    # 쿨타임 체크
    can_proceed, remaining = check_cooldown(channel_id)
    if not can_proceed:
        await message.reply(f"잠시만요! {remaining:.1f}초 후에 다시 시도해주세요.")
        return
    
    # 입력 중 표시
    async with message.channel.typing():
        response = await call_groq_api(channel_id, content)
    
    # 메시지 분할 전송
    chunks = split_message(response)
    for i, chunk in enumerate(chunks):
        if i == 0:
            await message.reply(chunk)
        else:
            await message.channel.send(chunk)


@bot.event
async def on_ready():
    """봇 준비 완료"""
    print(f"{bot.user} 봇이 시작되었습니다!")
    print(f"서버 {len(bot.guilds)}개에 연결됨")


@bot.event
async def on_message(message):
    """메시지 이벤트 처리"""
    # 봇 메시지 무시
    if message.author.bot:
        return
    
    # 봇 멘션 체크
    if bot.user.mentioned_in(message):
        # @everyone, @here 멘션 제외
        if message.mention_everyone:
            await bot.process_commands(message)
            return
            
        content = message.content.replace(f"<@{bot.user.id}>", "").replace(f"<@!{bot.user.id}>", "").strip()
        if content:
            await process_message(message, content)
            return
        else:
            await message.reply("메시지를 입력해주세요! 예: `@봇이름 안녕하세요`")
            return
    
    await bot.process_commands(message)


@bot.command(name="chat")
async def chat_command(ctx, *, message: str = ""):
    """AI와 대화하는 명령어"""
    if not message:
        await ctx.reply("메시지를 입력해주세요! 예: `!chat 안녕하세요`")
        return
    await process_message(ctx.message, message)


@bot.command(name="info")
async def info_command(ctx):
    """봇 정보 표시"""
    info_text = """**[봇 정보]**
모델: openai/gpt-oss-120b
API: Groq (무료 티어)
개발자: seonggyujo
이메일: whtjdrb020@gmail.com
GitHub: https://github.com/seonggyujo/discord-chatbot"""
    await ctx.reply(info_text)


if __name__ == "__main__":
    if not DISCORD_TOKEN:
        print("오류: DISCORD_BOT_TOKEN이 설정되지 않았습니다.")
        exit(1)
    if not GROQ_API_KEY:
        print("오류: GROQ_API_KEY가 설정되지 않았습니다.")
        exit(1)
    
    bot.run(DISCORD_TOKEN)
