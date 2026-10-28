"""The daily counter shared by every visitor. Plain code: no network, no credits."""

import threading
from datetime import date

from src.usage import DailyCounter


def test_the_count_starts_again_at_midnight():
    day = [date(2026, 10, 29)]
    counter = DailyCounter(today=lambda: day[0])
    counter.add()
    counter.add()
    assert counter.cases() == 2

    day[0] = date(2026, 10, 30)  # midnight passes
    assert counter.cases() == 0
    counter.add()
    assert counter.cases() == 1


def test_a_case_counted_right_after_midnight_belongs_to_the_new_day():
    day = [date(2026, 10, 29)]
    counter = DailyCounter(today=lambda: day[0])
    counter.add()
    day[0] = date(2026, 10, 30)
    counter.add()  # nobody read the count since midnight
    assert counter.cases() == 1


def test_visitors_clicking_at_the_same_time_never_lose_a_case():
    counter = DailyCounter()

    def visitor() -> None:
        for _ in range(200):
            counter.add()

    threads = [threading.Thread(target=visitor) for _ in range(20)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert counter.cases() == 20 * 200
