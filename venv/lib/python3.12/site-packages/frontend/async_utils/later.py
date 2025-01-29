import asyncio

__all__ = ['later_run', 'later_await', 'later_run_await']

from typing import Awaitable, Callable


def later_run(func: Callable, delay_seconds: float) -> None:
    async def c_later() -> None:
        await asyncio.sleep(delay_seconds)
        func()

    asyncio.create_task(c_later())


def later_await(awaitable: Awaitable, delay_seconds: float) -> None:
    async def c_later() -> None:
        await asyncio.sleep(delay_seconds)
        await awaitable

    asyncio.create_task(c_later())


def later_run_await(func: Callable[..., Awaitable], delay_seconds: float) -> None:
    async def c_later() -> None:
        await asyncio.sleep(delay_seconds)
        await func()

    asyncio.create_task(c_later())
