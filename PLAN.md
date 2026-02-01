# 디스코드 AI 챗봇 개발 계획서

## 1. 프로젝트 개요

| 항목 | 내용 |
|------|------|
| **목적** | Groq API(무료)를 사용한 24시간 디스코드 AI 챗봇 |
| **모델** | llama-3.3-70b-versatile |
| **서버** | Oracle Cloud Free Tier (ARM64, Ubuntu 22.04) |
| **GitHub** | https://github.com/seonggyujo/discord-chatbot |
| **개발자** | seonggyujo (whtjdrb020@gmail.com) |

---

## 2. 파일 구조

```
discord-chatbot/
├── bot.py                      # 메인 봇 코드
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
- **모델**: `llama-3.3-70b-versatile`
- **max_tokens**: 512 (최대 300자 응답)
- **System Prompt**:
  - 질문에 대한 답변만
  - 핵심만 짧게, 최대 300자 이내
  - 되묻는 질문 금지
  - 불필요한 인사말/부연설명 생략
  - 한국어로 대답

### 3.3 컨텍스트 관리
- 채널별 최근 **5개 메시지** 유지 (메모리 저장)
- 봇 재시작 시 초기화 (의도된 동작)
- `collections.deque(maxlen=5)` 사용

### 3.4 Rate Limit 보호
- **채널별 쿨타임**: 3초
- **429 에러 처리**: "API 요청 한도 초과" 안내 메시지 출력

### 3.5 응답 처리
- 최대 **300자 이내** 응답 (핵심만 짧게)
- 2000자 초과 시 **분할 전송** (Discord 메시지 제한)
- "입력 중..." 표시 (`channel.typing()`)

---

## 4. 코드 상세 설계

### 4.1 bot.py 구조

```python
import os
from collections import defaultdict, deque
from time import time

import discord
from discord.ext import commands
import aiohttp
from dotenv import load_dotenv

# 환경변수
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# 설정
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.3-70b-versatile"
SYSTEM_PROMPT = """너는 디스코드 챗봇이야.
질문에 대한 답변만 해. 핵심만 짧게 말해.
최대 300자 이내로 답변해.
되묻는 질문 하지마.
불필요한 인사말이나 부연설명 생략해.
한국어로 대답해."""
MAX_CONTEXT = 5
COOLDOWN_SECONDS = 3
MAX_MESSAGE_LENGTH = 2000

# 상태 저장 (메모리)
conversation_history = defaultdict(lambda: deque(maxlen=MAX_CONTEXT))
last_request_time = defaultdict(float)

# 봇 설정
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)
```

### 4.2 Groq API 호출

```python
async def call_groq_api(channel_id: int, user_message: str) -> str:
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
    
    async with aiohttp.ClientSession() as session:
        async with session.post(GROQ_API_URL, headers=headers, json=payload) as resp:
            if resp.status == 429:
                return "API 요청 한도를 초과했습니다. 잠시 후 다시 시도해주세요."
            
            if resp.status != 200:
                return f"API 오류가 발생했습니다. (상태 코드: {resp.status})"
            
            data = await resp.json()
            assistant_message = data["choices"][0]["message"]["content"]
            
            # 어시스턴트 응답도 컨텍스트에 저장
            conversation_history[channel_id].append({
                "role": "assistant",
                "content": assistant_message
            })
            
            return assistant_message
```

### 4.3 쿨타임 체크

```python
def check_cooldown(channel_id: int) -> tuple[bool, float]:
    current_time = time()
    elapsed = current_time - last_request_time[channel_id]
    
    if elapsed < COOLDOWN_SECONDS:
        return False, COOLDOWN_SECONDS - elapsed
    
    last_request_time[channel_id] = current_time
    return True, 0
```

### 4.4 메시지 분할

```python
def split_message(text: str, max_length: int = 2000) -> list[str]:
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
```

### 4.5 봇 정보 명령어

```python
@bot.command(name="info")
async def info_command(ctx: commands.Context):
    info_text = """**[봇 정보]**
모델: llama-3.3-70b-versatile
API: Groq (무료 티어)
개발자: seonggyujo
이메일: whtjdrb020@gmail.com
GitHub: https://github.com/seonggyujo/discord-chatbot"""
    await ctx.reply(info_text)
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
| 429 Rate Limit | "API 요청 한도 초과" 메시지 |
| API 연결 실패 | "API 연결 오류" 메시지 |
| 빈 메시지 | "메시지를 입력해주세요" 안내 |
| 쿨타임 | "N초 후 다시 시도해주세요" |
| 예외 발생 | 로그 출력 + 사용자에게 오류 안내 |

---

## 10. 특이사항

- **포트 개방 불필요**: Discord WebSocket은 outbound 연결만 사용
- **Nginx 설정 불필요**: 웹 서버 없음
- **메모리 사용량**: 매우 적음 (대화 기록만 저장)
- **Groq 무료 티어 제한**: 30 req/min, 6000 tokens/min
