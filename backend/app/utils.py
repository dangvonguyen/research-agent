import asyncio
from collections.abc import Callable, Coroutine
from typing import Any, TypeVar

T = TypeVar("T")
U = TypeVar("U")


async def bulk_run(
    async_func: Callable[[U], Coroutine[None, None, T]],
    items: list[U],
    **kwargs: Any,
) -> list[T]:
    """
    Run an async function on multiple items concurrently.
    """
    tasks = [async_func(item, **kwargs) for item in items]
    return await asyncio.gather(*tasks)
