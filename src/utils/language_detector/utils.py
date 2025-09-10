import asyncio
import logging
from functools import wraps


def async_retry(max_retries: int, delay: float):
    def decorator(coro):
        @wraps(coro)
        async def wrapper(*args, **kwargs):
            for attempt in range(1, max_retries + 2):
                try:
                    return await coro(*args, **kwargs)
                except Exception as e:
                    if attempt > max_retries:
                        logging.error(f'❌ Failed after {max_retries + 1} attempts: {e}')
                        raise

                    wait_time = delay * (2 ** (attempt - 1))  # Optional: exponential backoff
                    logging.warning(
                        f'🔁 Attempt {attempt} failed: {e}. '
                        f'Retrying in {wait_time:.1f}s... '
                        f'({max_retries - attempt + 1} attempts left)'
                    )
                    await asyncio.sleep(wait_time)
            return None

        return wrapper

    return decorator
