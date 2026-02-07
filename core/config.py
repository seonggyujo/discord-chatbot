"""봇 설정 및 상수"""

from __future__ import annotations

import logging
import os

from dotenv import load_dotenv  # type: ignore

# 환경변수 로드
load_dotenv()

# 환경변수
DISCORD_TOKEN: str | None = os.getenv("DISCORD_BOT_TOKEN")
GROQ_API_KEY: str | None = os.getenv("GROQ_API_KEY")

# API 설정
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "openai/gpt-oss-120b"

# 봇 설정
MAX_CONTEXT = 10
COOLDOWN_SECONDS = 3
MAX_MESSAGE_LENGTH = 2000
MAX_RETRIES = 2
API_TIMEOUT_SECONDS = 30

# 시스템 프롬프트
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

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("discord-chatbot")
