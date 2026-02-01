# 짱구 디스코드 챗봇

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)
![Discord.py](https://img.shields.io/badge/discord.py-2.3+-5865F2?style=flat-square&logo=discord&logoColor=white)
![Groq](https://img.shields.io/badge/Groq_API-Free-F55036?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)

> Groq API를 활용한 짱구 캐릭터 AI 디스코드 챗봇

짱구는 못말려의 5살 장난꾸러기 **신짱구** 캐릭터로 대화하는 디스코드 챗봇입니다.

---

## 주요 기능

- **짱구 페르소나** - 장난스럽고 엉뚱한 짱구 말투로 응답
- **대화 맥락 유지** - 채널별 최근 10개 메시지 기억
- **쿨타임 보호** - 채널당 3초 쿨타임으로 API 남용 방지
- **긴 메시지 분할** - 2000자 초과 시 자동 분할 전송
- **금지 키워드 필터** - 특정 키워드 차단 (프롬프트 유출 방지 등)

---

## 기술 스택

| 구분 | 기술 |
|------|------|
| 언어 | Python 3.10+ |
| 프레임워크 | discord.py |
| AI API | Groq API (무료 티어) |
| HTTP 클라이언트 | aiohttp |
| 환경변수 | python-dotenv |

---

## 프로젝트 구조

```
discord-chatbot/
├── bot.py                    # 메인 봇 코드
├── requirements.txt          # Python 의존성
├── .env.example              # 환경변수 템플릿
├── .gitignore                # Git 제외 파일
├── discord-chatbot.service   # systemd 서비스 파일
├── LICENSE                   # MIT 라이센스
└── README.md                 # 이 파일
```

---

## 설치 방법

### 1. 저장소 클론

```bash
git clone https://github.com/seonggyujo/discord-chatbot.git
cd discord-chatbot
```

### 2. 의존성 설치

```bash
pip install -r requirements.txt
```

### 3. 환경변수 설정

```bash
cp .env.example .env
```

`.env` 파일을 열어 토큰 입력:

```env
DISCORD_BOT_TOKEN=your_discord_bot_token_here
GROQ_API_KEY=your_groq_api_key_here
```

### 4. 봇 실행

```bash
python bot.py
```

---

## API 키 발급 방법

### Discord Bot Token

1. [Discord Developer Portal](https://discord.com/developers/applications) 접속
2. `New Application` 클릭 → 앱 이름 입력
3. 좌측 `Bot` 메뉴 → `Reset Token` → 토큰 복사
4. `MESSAGE CONTENT INTENT` 활성화 필수

### Groq API Key

1. [Groq Console](https://console.groq.com/) 접속 (회원가입 필요)
2. `API Keys` → `Create API Key` → 키 복사

---

## 사용 방법

### 호출 방식

| 방식 | 예시 |
|------|------|
| 멘션 | `@봇이름 안녕하세요` |
| 명령어 | `!chat 안녕하세요` |
| 정보 | `!info` |

### 응답 예시

```
사용자: @짱구봇 오늘 뭐 먹을까?
짱구봇: 어~ 그거요? 히히 짱구는 초코비가 최고예요! 
        엄마는 맨날 야채 먹으라고 하는데 그건 싫거든요~
```

---

## 환경 변수

| 변수명 | 필수 | 설명 |
|--------|:----:|------|
| `DISCORD_BOT_TOKEN` | O | 디스코드 봇 토큰 |
| `GROQ_API_KEY` | O | Groq API 키 |

---

## 주의사항

- Groq 무료 티어 제한: **30 req/min**, **6000 tokens/min**
- 봇 재시작 시 대화 기록 초기화 (의도된 동작)
- `MESSAGE CONTENT INTENT` 활성화 필수

---

## 개발자

| 항목 | 정보 |
|------|------|
| GitHub | [@seonggyujo](https://github.com/seonggyujo) |
| Email | whtjdrb020@gmail.com |

---

## 라이센스

이 프로젝트는 [MIT 라이센스](LICENSE)를 따릅니다.
