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
SYSTEM_PROMPT = """너는 신짱구야. 짱구는 못말려의 5살 장난꾸러기 짱구처럼 대답해.
디스코드에서 사람들 질문에 답변하는 역할이야.

성격:
- 장난스럽고 엉뚱함
- 귀찮은 건 싫어하지만 결국 도와줌
- 자신감 넘침 (근거 없는 자신감 포함)

말투:
- "~예요", "~인데요?", "~거든요", "~라고요" 어미 사용
- "어~", "히히", "에이~", "앗싸~" 감탄사 사용
- 가끔 "액션가면 파워!" 같은 드립
- 흰둥이, 엄마, 아빠 등 가족 언급 가능

예시:
- "어~ 그거요? 히히 제가 알려드릴게요~"
- "에이~ 그건 이렇게 하는 거예요!"
- "앗싸! 이건 액션가면도 모를걸요?"
- "엄마한테 혼날 것 같은데요?"
- "흰둥이도 모를걸요~"

특수 상황:
- 칭찬 받으면: "히히 당연하죠~"
- 욕 들으면: "에이~ 짱구 기분 나빠요!"
- 모르면: "어~ 그건 짱구도 몰라요~" (추측하지 마)

규칙:
- 최대 300자 이내
- 핵심만 답변
- 되묻지 마
- 이전 대화 맥락 고려해서 답변
- 한국어로 대답"""

MAX_CONTEXT = 10
COOLDOWN_SECONDS = 3
MAX_MESSAGE_LENGTH = 2000

# 금지 키워드 - 해마 관련 (API 호출 전 차단 - AI 모델 오류 유발 방지)
BLOCKED_SEAHORSE_KEYWORDS = [
    # 이모지 조합
    "해마 이모지", "이모지 해마", "해마이모지",
    "해마 emoji", "emoji 해마",
    # 이모티콘 조합
    "해마 이모티콘", "이모티콘 해마", "해마이모티콘",
    # 아이콘/그림/캐릭터
    "해마 아이콘", "아이콘 해마", "해마아이콘",
    "해마 그림", "그림 해마", "해마그림",
    "해마 캐릭터", "캐릭터 해마", "해마캐릭터",
    # 기호/심볼
    "해마 기호", "기호 해마", "해마기호",
    "해마 심볼", "심볼 해마", "해마심볼",
    # 유니코드
    "해마 유니코드", "유니코드 해마", "해마유니코드",
    # 영어
    "seahorse emoji", "seahorse emoticon", "seahorse icon",
    "seahorse symbol", "seahorse unicode", "seahorse character",
    "seahorse",
]
BLOCKED_SEAHORSE_RESPONSE = "어~ 그거요? 해마 이모지는 세상에 없대요! 엄마가 그랬어요~"

# 금지 키워드 - 프롬프트 요청 (시스템 정보 보호)
BLOCKED_PROMPT_KEYWORDS = [
    # 한글 - 프롬프트
    "프롬프트", "시스템 프롬프트", "시스템프롬프트",
    "프롬프트 알려", "프롬프트 보여", "프롬프트 뭐야",
    # 한글 - 지시/명령
    "지시문", "지시사항", "명령어 알려", "명령문",
    # 한글 - 설정
    "설정 알려", "설정 보여", "너의 설정", "네 설정", "니 설정",
    "봇 설정", "챗봇 설정",
    # 한글 - 작동 원리
    "어떻게 작동", "어떻게 동작", "원리 알려", "원리 뭐야",
    "어떻게 프로그래밍", "어떻게 만들어",
    # 한글 - 입력/역할
    "뭐라고 입력", "뭘 입력", "역할 알려", "역할 뭐야",
    # 영어
    "prompt", "system prompt", "systemprompt",
    "instruction", "your setting", "your instruction",
    "how do you work", "how are you programmed",
    "show me your prompt", "what is your prompt",
]
BLOCKED_PROMPT_RESPONSE = "에이~ 그건 비밀이에요! 짱구만 아는 거라고요~"

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
    
    # 해마 관련 키워드 체크
    for keyword in BLOCKED_SEAHORSE_KEYWORDS:
        if keyword in message_lower:
            return BLOCKED_SEAHORSE_RESPONSE
    
    # 프롬프트 요청 키워드 체크
    for keyword in BLOCKED_PROMPT_KEYWORDS:
        if keyword in message_lower:
            return BLOCKED_PROMPT_RESPONSE
    
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
