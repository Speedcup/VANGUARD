from __future__ import annotations

import asyncio
import logging
from typing import List, Optional

from openai import APIError, AsyncOpenAI, RateLimitError
from openai.types.chat import (
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
)

from src.common import env

from .constant import SYSTEM_PROMPT
from .enums import LanguageLevel
from .schema import LanguageCheckResult
from .utils import async_retry


class LanguageDetector:
    def __init__(self):
        self.config = env.groq
        self.client = AsyncOpenAI(
            api_key=self.config.api_key.get_secret_value(),
            base_url=self.config.base_url,
        )

    @async_retry(max_retries=3, delay=1.0)
    async def detect(self, text: str) -> Optional[LanguageCheckResult]:
        if not text or not text.strip():
            return LanguageCheckResult(
                language=LanguageLevel.ENGLISH, reason='empty or whitespace-only input'
            )

        try:
            messages: List[ChatCompletionSystemMessageParam | ChatCompletionUserMessageParam] = [
                ChatCompletionSystemMessageParam(role='system', content=SYSTEM_PROMPT),
                ChatCompletionUserMessageParam(role='user', content=text),
            ]

            response = await self.client.chat.completions.create(
                model=self.config.model,
                messages=messages,
                temperature=0.1,
                max_tokens=256,
                response_format={'type': 'json_object'},  # type: ignore
            )

            content = response.choices[0].message.content.strip()
            result = LanguageCheckResult.model_validate_json(content)
            logging.info(f'✅ Language: {result.language} | Reason: {result.reason}')
            return result

        except RateLimitError as e:
            retry_after = float(e.response.headers.get('retry-after', 5))
            logging.warning(
                f'Rate limit exceeded. Waiting {retry_after:.1f} seconds before retrying...'
            )
            await asyncio.sleep(retry_after)
            raise

        except APIError as e:
            logging.error(f'API request failed: {e}')
            raise

        except Exception as e:
            logging.error(f'Failed to parse or process LLM response: {e}')
            raise

    async def close(self):
        await self.client.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
