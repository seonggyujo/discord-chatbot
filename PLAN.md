# 디스코드 AI 챗봇 개발 계획서

## 1. 프로젝트 개요

| 항목 | 내용 |
|------|------|
| **목적** | Groq API(무료)를 사용한 24시간 디스코드 AI 챗봇 |
| **모델** | openai/gpt-oss-120b |
| **서버** | Oracle Cloud Free Tier (ARM64, Ubuntu 22.04) |
| **GitHub** | https://github.com/seonggyujo/discord-chatbot |
| **개발자** | seonggyujo (whtjdrb020@gmail.com) |

---

## 2. 파일 구조

```
discord-chatbot/
├── bot.py                      # 진입점 (봇 초기화, 이벤트 루프)
├── core/                       # 핵심 모듈
│   ├── __init__.py
│   ├── config.py               # 설정, 상수, 환경변수, 로깅
│   ├── api.py                  # Groq API 클라이언트
│   └── filters.py              # 키워드 필터링 (정규식)
├── cogs/                       # Discord Cog 모듈
│   ├── __init__.py
│   ├── chat.py                 # 채팅 명령어 및 멘션 처리
│   └── info.py                 # 봇 정보 명령어
├── requirements.txt            # Python 의존성
├── .env.example                # 환경변수 템플릿
├── .gitignore                  # .env 등 제외
├── discord-chatbot.service     # systemd 서비스 파일
└── PLAN.md                     # 이 계획서
```

---

## 3. 핵심 기능 명세

### 3.1 호출 방식
- `!chat <메시지>` - AI와 대화
- `@봇이름 <메시지>` - AI와 대화 (멘션)
- `!info` - 봇 정보 표시

### 3.2 AI 설정
- **엔드포인트**: `https://api.groq.com/openai/v1/chat/completions`
- **모델**: `openai/gpt-oss-120b`
- **max_tokens**: 512 (최대 300자 응답)
- **System Prompt**: 짱구 캐릭터 페르소나
  - 장난스럽고 엉뚱한 말투
  - 핵심만 짧게, 최대 300자 이내
  - 되묻는 질문 금지
  - 이전 대화 맥락 고려
  - 한국어로 대답

### 3.3 컨텍스트 관리
- 채널별 최근 **10개 메시지** 유지 (메모리 저장)
- 봇 재시작 시 초기화 (의도된 동작)
- `collections.deque(maxlen=10)` 사용
- **1시간 비활성 채널 자동 정리** (`discord.ext.tasks`)

### 3.4 Rate Limit 보호
- **채널별 쿨타임**: 3초
- **429 에러 처리**: Retry-After 헤더 기반 자동 재시도 (최대 2회)
- 재시도 실패 시 "API 요청 한도 초과" 안내 메시지 출력

### 3.5 응답 처리
- 최대 **300자 이내** 응답 (핵심만 짧게)
- 2000자 초과 시 **분할 전송** (Discord 메시지 제한)
- "입력 중..." 표시 (`channel.typing()`)

### 3.6 보안 필터
- **해마 관련 키워드 차단**: AI 모델 오류 유발 방지 (정규식 기반)
- **프롬프트 유출 방지**: 시스템 프롬프트 요청 차단 (정규식 기반)

---

## 4. 코드 상세 설계

### 4.1 core/config.py - 설정

```python
import os
import logging
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "openai/gpt-oss-120b"
MAX_CONTEXT = 10
COOLDOWN_SECONDS = 3
MAX_MESSAGE_LENGTH = 2000
MAX_RETRIES = 2
API_TIMEOUT_SECONDS = 30

SYSTEM_PROMPT = """너는 신짱구야. ..."""

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("discord-chatbot")
```

### 4.2 core/api.py - Groq API 클라이언트

```python
class GroqClient:
    """aiohttp 세션 재사용, 타임아웃, 재시도, 응답 검증"""

    async def start(self) -> None: ...
    async def close(self) -> None: ...
    async def chat(self, messages) -> tuple[str | None, str | None]:
        """성공: (응답, None), 실패: (None, 에러메시지)"""
        # - 30초 타임아웃
        # - 429/5xx 시 최대 2회 재시도
        # - 응답 구조 검증 (choices 배열 확인)
        ...
```

### 4.3 core/filters.py - 키워드 필터링

```python
import re

# 정규식 패턴을 미리 컴파일하여 O(1) 매칭
_SEAHORSE_PATTERN = re.compile("|".join(re.escape(kw) for kw in KEYWORDS))
_PROMPT_PATTERN = re.compile("|".join(re.escape(kw) for kw in KEYWORDS))

def check_blocked(message: str) -> str | None:
    """차단 시 응답 문자열 반환, 통과 시 None"""
    ...
```

### 4.4 cogs/chat.py - 채팅 Cog

```python
class ChatCog(commands.Cog):
    def __init__(self, bot):
        self.api = GroqClient()
        self.conversation_history = defaultdict(lambda: deque(maxlen=10))
        self.last_request_time = defaultdict(float)

    async def cog_load(self): ...    # API 세션 시작, 정리 태스크 시작
    async def cog_unload(self): ...  # 리소스 정리

    def check_cooldown(self, channel_id) -> tuple[bool, float]: ...
    def split_message(text, max_length=2000) -> list[str]: ...
    async def process_message(self, message, content): ...

    @commands.Cog.listener()
    async def on_message(self, message): ...  # 멘션 처리

    @commands.command(name="chat")
    async def chat_command(self, ctx, *, message): ...

    @tasks.loop(hours=1)
    async def cleanup_inactive(self): ...  # 비활성 채널 정리
```

### 4.5 cogs/info.py - 정보 Cog

```python
class InfoCog(commands.Cog):
    @commands.command(name="info")
    async def info_command(self, ctx):
        """모델, API, 개발자 정보 표시"""
        ...
```

### 4.6 bot.py - 진입점

```python
async def main() -> None:
    async with bot:
        await bot.load_extension("cogs.chat")
        await bot.load_extension("cogs.info")
        await bot.start(DISCORD_TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 5. 의존성

### requirements.txt

```
discord.py>=2.3.0
aiohttp>=3.9.0
python-dotenv>=1.0.0
```

---

## 6. 환경변수

### .env.example

```
DISCORD_BOT_TOKEN=your_discord_bot_token_here
GROQ_API_KEY=your_groq_api_key_here
```

### .gitignore

```
.env
__pycache__/
*.pyc
```

---

## 7. systemd 서비스

### discord-chatbot.service

```ini
[Unit]
Description=Discord AI Chatbot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/discord-chatbot
ExecStart=/usr/bin/python3 bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

---

## 8. 서버 배포 절차

```bash
# 1. 클론
cd ~
git clone https://github.com/seonggyujo/discord-chatbot.git
cd discord-chatbot

# 2. 의존성 설치
pip3 install -r requirements.txt

# 3. 환경변수 설정
cp .env.example .env
nano .env  # 토큰 입력

# 4. systemd 등록
sudo cp discord-chatbot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable discord-chatbot
sudo systemctl start discord-chatbot

# 5. 확인
sudo systemctl status discord-chatbot
sudo journalctl -u discord-chatbot -f
```

---

## 9. 에러 처리

| 에러 | 처리 방식 |
|------|-----------|
| 429 Rate Limit | 자동 재시도 (최대 2회) → 실패 시 안내 메시지 |
| API 연결 실패 | 자동 재시도 (최대 2회) → 실패 시 안내 메시지 |
| API 응답 검증 실패 | "API 응답이 올바르지 않습니다" 안내 |
| 빈 메시지 | "메시지를 입력해주세요" 안내 |
| 쿨타임 | "N초 후 다시 시도해주세요" |
| 예외 발생 | 로그 출력 + 사용자에게 오류 안내 |
| 해마/프롬프트 키워드 | 사전 차단 응답 반환 |

---

## 10. 특이사항

- **포트 개방 불필요**: Discord WebSocket은 outbound 연결만 사용
- **Nginx 설정 불필요**: 웹 서버 없음
- **메모리 사용량**: 매우 적음 (대화 기록만 저장, 비활성 채널 자동 정리)
- **Groq 무료 티어 제한**: 30 req/min, 6000 tokens/min
- **로깅**: `logging` 모듈 사용 (타임스탬프, 레벨 포함)
- **TCP 연결 풀링**: `aiohttp.ClientSession` 재사용으로 성능 최적화
- **모듈화**: Cog 기반 구조로 기능 분리 및 확장 용이
