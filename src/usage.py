"""The daily case counter shared by every visitor (session limits reset when the page reloads)."""

import threading
from collections.abc import Callable
from datetime import date


class DailyCounter:
    """Cases the whole app ran today; it starts again at 0 when the day changes.

    Several visitors can click at the same time (Streamlit runs each one in its own thread),
    so every read and write happens under one lock.
    """

    def __init__(self, today: Callable[[], date] = date.today) -> None:
        self._today = today  # replaceable in tests, to simulate midnight
        self._lock = threading.Lock()
        self._day: date | None = None
        self._cases = 0

    def _start_new_day_if_needed(self) -> None:
        """Call only while holding the lock."""
        if self._day != self._today():
            self._day, self._cases = self._today(), 0

    def cases(self) -> int:
        with self._lock:
            self._start_new_day_if_needed()
            return self._cases

    def add(self) -> None:
        with self._lock:
            self._start_new_day_if_needed()
            self._cases += 1
