import asyncio
import logging
import random
from collections.abc import Callable, Coroutine
from functools import wraps
from typing import Any, ParamSpec, TypeVar

logger = logging.getLogger(__name__)

P = ParamSpec('P')
R = TypeVar('R')


def backoff(
    start_sleep_time: float = 0.1,
    factor: float = 2,
    border_sleep_time: float = 10,
    max_retries: int = 5,
    exceptions: tuple[type[BaseException], ...] = (Exception,),
) -> Callable[
    [Callable[P, Coroutine[Any, Any, R]]],
    Callable[P, Coroutine[Any, Any, R]],
]:
    """
    Повторный вызов async-функции при ошибке внешнего сервиса.

    Экспоненциальный рост паузы (factor) до border_sleep_time
    со случайным разбросом (full jitter), чтобы снизить пик нагрузки.
    """

    def func_wrapper(
        func: Callable[P, Coroutine[Any, Any, R]],
    ) -> Callable[P, Coroutine[Any, Any, R]]:
        @wraps(func)
        async def inner(*args: P.args, **kwargs: P.kwargs) -> R:
            n = 0
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as exc:
                    if attempt == max_retries:
                        raise

                    base_delay = start_sleep_time * (factor ** n)
                    if base_delay >= border_sleep_time:
                        base_delay = border_sleep_time
                    else:
                        n += 1
                    sleep_time = random.uniform(0, base_delay)

                    logger.warning(
                        'Backoff for %s: %s. Retry in %.1fs',
                        func.__name__,
                        exc,
                        sleep_time,
                    )
                    await asyncio.sleep(sleep_time)

            raise RuntimeError('unreachable')

        return inner

    return func_wrapper
