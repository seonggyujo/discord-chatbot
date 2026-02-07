"""Groq API 클라이언트 - 세션 재사용, 타임아웃, 재시도, 응답 검증"""

from __future__ import annotations

import asyncio

import aiohttp  # type: ignore

from core.config import (
    API_TIMEOUT_SECONDS,
    GROQ_API_KEY,
    GROQ_API_URL,
    MAX_RETRIES,
    MODEL,
    logger,
)


class GroqClient:
    """Groq API 호출을 관리하는 클라이언트.

    - aiohttp.ClientSession을 재사용하여 TCP 연결 풀링
    - 요청 타임아웃 설정으로 무한 대기 방지
    - 일시적 오류(429, 5xx)에 대한 재시도 로직
    - API 응답 구조 검증
    """

    def __init__(self) -> None:
        self.session: aiohttp.ClientSession | None = None

    async def start(self) -> None:
        """HTTP 세션을 시작합니다."""
        timeout = aiohttp.ClientTimeout(total=API_TIMEOUT_SECONDS)
        self.session = aiohttp.ClientSession(timeout=timeout)
        logger.info("Groq API 클라이언트 세션 시작")

    async def close(self) -> None:
        """HTTP 세션을 종료합니다."""
        if self.session and not self.session.closed:
            await self.session.close()
            logger.info("Groq API 클라이언트 세션 종료")

    async def chat(
        self, messages: list[dict[str, str]]
    ) -> tuple[str | None, str | None]:
        """Groq API에 채팅 요청을 보냅니다.

        Returns:
            (응답 텍스트, None) - 성공 시
            (None, 에러 메시지) - 실패 시
        """
        if not self.session or self.session.closed:
            await self.start()

        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": MODEL,
            "messages": messages,
            "max_tokens": 512,
            "temperature": 0.7,
        }

        last_error = "오류가 발생했습니다. 잠시 후 다시 시도해주세요."

        for attempt in range(MAX_RETRIES):
            try:
                async with self.session.post(
                    GROQ_API_URL, headers=headers, json=payload
                ) as resp:
                    # Rate Limit 처리 (재시도 가능)
                    if resp.status == 429:
                        if attempt < MAX_RETRIES - 1:
                            retry_after = float(
                                resp.headers.get("Retry-After", "2")
                            )
                            logger.warning(
                                "Rate limited, %s초 후 재시도 (시도 %d/%d)",
                                retry_after,
                                attempt + 1,
                                MAX_RETRIES,
                            )
                            await asyncio.sleep(retry_after)
                            continue
                        return (
                            None,
                            "API 요청 한도를 초과했습니다. 잠시 후 다시 시도해주세요.",
                        )

                    # 기타 HTTP 오류 (재시도 가능)
                    if resp.status != 200:
                        last_error = (
                            f"API 오류가 발생했습니다. (상태 코드: {resp.status})"
                        )
                        logger.warning(
                            "API 오류 상태 코드: %d (시도 %d/%d)",
                            resp.status,
                            attempt + 1,
                            MAX_RETRIES,
                        )
                        if attempt < MAX_RETRIES - 1:
                            await asyncio.sleep(1)
                            continue
                        return None, last_error

                    # 응답 파싱 및 구조 검증
                    data = await resp.json()

                    choices = data.get("choices")
                    if not choices or not isinstance(choices, list):
                        logger.error("API 응답에 choices가 없음: %s", data)
                        return (
                            None,
                            "API 응답이 올바르지 않습니다. 잠시 후 다시 시도해주세요.",
                        )

                    content = choices[0].get("message", {}).get("content", "")
                    if not content:
                        logger.warning("API 응답이 비어 있음")
                        return None, "빈 응답을 받았습니다. 다시 시도해주세요."

                    return content, None

            except aiohttp.ClientError as e:
                last_error = "API 연결 오류가 발생했습니다. 잠시 후 다시 시도해주세요."
                logger.error(
                    "API 연결 오류 (시도 %d/%d): %s",
                    attempt + 1,
                    MAX_RETRIES,
                    e,
                )
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(1)
                    continue
                return None, last_error

            except Exception as e:
                logger.exception("예기치 않은 예외 발생: %s", e)
                return None, "오류가 발생했습니다. 잠시 후 다시 시도해주세요."

        return None, last_error
