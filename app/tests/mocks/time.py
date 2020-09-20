import datetime
import pytz
import typing

from airq.lib.clock import _clock


class MockDateTime:
    def __init__(self, dt: datetime.datetime):
        self.dt = dt
        self._old_impl = None

    def __enter__(self):
        self._old_impl = _clock._impl
        _clock._impl = self

    def __exit__(self, *args, **kwargs):
        _clock._impl = self._old_impl

    def now(self, tz: typing.Optional[pytz.BaseTzInfo] = None) -> datetime.datetime:
        return self.dt

    def advance(self, amount: int = 1):
        delta = datetime.timedelta(seconds=amount)
        if amount > 0:
            self.dt += delta
        else:
            self.dt -= delta
