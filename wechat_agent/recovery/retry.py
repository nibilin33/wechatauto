from __future__ import annotations

import time
from typing import Callable, TypeVar

T = TypeVar("T")

_DEFAULT_DELAYS = (0.5, 1.0, 2.0)


def retry(
    fn: Callable[[], T],
    *,
    delays: tuple[float, ...] = _DEFAULT_DELAYS,
    exceptions: tuple[type[BaseException], ...] = (Exception,),
    on_retry: Callable[[int, BaseException], None] | None = None,
) -> T:
    """
    Call *fn* and retry on failure with exponential-ish back-off.

    Parameters
    ----------
    fn:         zero-argument callable to attempt
    delays:     sleep durations between attempts (len = max retries)
    exceptions: tuple of exception types that trigger a retry
    on_retry:   optional callback(attempt_index, error) before sleeping
    """
    last_exc: BaseException | None = None
    for attempt, delay in enumerate(delays):
        try:
            return fn()
        except exceptions as exc:
            last_exc = exc
            if on_retry is not None:
                on_retry(attempt, exc)
            time.sleep(delay)

    # Final attempt with no sleep after.
    try:
        return fn()
    except exceptions as exc:
        raise exc from last_exc
