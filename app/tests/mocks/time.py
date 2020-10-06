import datetime
import pytz
import typing

from airq.lib.clock import _clock


class MockDateTime:
    def __init__(self, dt: datetime.datetime):
        self.dt = dt

    def __enter__(self):
        self.start()

    def __exit__(self, *args, **kwargs):
        self.stop()

    def start(self) -> "MockDateTime":
        self._old_impl = _clock._impl
        _clock._impl = self  # type: ignore
        return self

    def stop(self):
        _clock._impl = self._old_impl

    def now(self, tz: typing.Optional[pytz.BaseTzInfo] = None) -> datetime.datetime:
        return self.dt

    def advance(self, amount: int = 1) -> datetime.datetime:
        delta = datetime.timedelta(seconds=amount)
        if amount > 0:
            self.dt += delta
        else:
            self.dt -= delta
        return self.dt
