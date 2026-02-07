"""키워드 필터링 (정규식 기반)"""

from __future__ import annotations

import re

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

BLOCKED_SEAHORSE_RESPONSE = "어~ 그거요? 해마 이모지는 세상에 없대요! 엄마가 그랬어요~"
BLOCKED_PROMPT_RESPONSE = "에이~ 그건 비밀이에요! 짱구만 아는 거라고요~"

# 정규식 패턴을 미리 컴파일하여 검색 성능 향상
_SEAHORSE_PATTERN = re.compile(
    "|".join(re.escape(kw) for kw in BLOCKED_SEAHORSE_KEYWORDS)
)
_PROMPT_PATTERN = re.compile(
    "|".join(re.escape(kw) for kw in BLOCKED_PROMPT_KEYWORDS)
)


def check_blocked(message: str) -> str | None:
    """차단된 키워드 검사.

    차단 시 응답 문자열 반환, 통과 시 None 반환.
    """
    message_lower = message.lower()

    if _SEAHORSE_PATTERN.search(message_lower):
        return BLOCKED_SEAHORSE_RESPONSE

    if _PROMPT_PATTERN.search(message_lower):
        return BLOCKED_PROMPT_RESPONSE

    return None
