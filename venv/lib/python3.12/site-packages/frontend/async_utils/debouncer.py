import time
from typing import Awaitable, Callable, Union

from .later import later_run_await

__all__ = ['Debouncer']


class Debouncer:
    time_between_runs: float
    ignore_extra: bool
    _last_run_time: float
    _pending_requests: int

    def __init__(self, time_between_runs: float, ignore_extra: bool) -> None:
        self.time_between_runs = time_between_runs
        self.ignore_extra = ignore_extra
        self._last_run_time = 0
        self._pending_requests = 0

    def debounced_run(self, func: Callable) -> None:
        self._helper(func, action='run')

    def debounced_run_await(self, func: Callable[..., Awaitable]) -> None:
        self._helper(func, action='run_await')

    def debounced_await(self, awaitable: Awaitable) -> None:
        self._helper(awaitable, action='await')

    def _helper(self, what: Union[Callable, Awaitable], action: str) -> None:
        self._pending_requests += 1

        async def inner() -> None:
            if self.ignore_extra and self._pending_requests == 0:
                return
            now = time.time()
            remaining_delay = self.time_between_runs - (now - self._last_run_time)
            if remaining_delay < 0 < self._pending_requests:
                if action == 'run':
                    what()  # type: ignore
                elif action == 'run_await':
                    await what()  # type: ignore
                elif action == 'await':
                    await what  # type: ignore
                self._pending_requests = 0
                self._last_run_time = now
            else:
                later_run_await(inner, remaining_delay)

        later_run_await(inner, 0)
        later_run_await(inner, self.time_between_runs)


# todo there's some bug here
'''
ERROR:    Task exception was never retrieved
future: <Task finished name='Task-66' coro=<later_run_await.<locals>.c_later() done, defined at /Users/pragyagarwal/MW/async_utils/later.py:25> exception=RuntimeError('cannot reuse already awaited coroutine')>
Traceback (most recent call last):
  File "/Users/pragyagarwal/MW/async_utils/later.py", line 27, in c_later
    await func()
  File "/Users/pragyagarwal/MW/async_utils/debouncer.py", line 44, in inner
    await what  # type: ignore
RuntimeError: cannot reuse already awaited coroutine
DEBUG:    server > Frame(fin=True, opcode=1, data=b'[{"component_id": null, "action": "run_javascript", "data": {"javascript": "get_editor_content(4343042448)"}, "callback_id": 4}]', rsv1=False, rsv2=False, rsv3=False)
DEBUG:    server > Frame(fin=True, opcode=9, data=b'\xd8,\x07\xcd', rsv1=False, rsv2=False, rsv3=False)
DEBUG:    server - event = data_received(<10 bytes>)
DEBUG:    server < Frame(fin=True, opcode=10, data=b'\xd8,\x07\xcd'
'''
