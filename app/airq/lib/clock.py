import datetime
import pytz
import typing


class _Clock:
    """Wraps datetime methods for easy mocking.

    Should be internal to this module.
    """

    def __init__(self, impl: typing.Type[datetime.datetime] = datetime.datetime):
        self._impl = impl

    def now(self, timezone: str = "America/Los_Angeles") -> datetime.datetime:
        return self._impl.now(tz=pytz.timezone(timezone))

    def timestamp(self) -> int:
        return int(self.now().timestamp())


_clock = _Clock()
now = _clock.now
timestamp = _clock.timestamp
