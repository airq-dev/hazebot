import datetime
import pytz


class MockDateTime:
    def __init__(self, dt: datetime.datetime):
        self.dt = dt

    def now(self, tz: pytz.BaseTzInfo) -> datetime.datetime:
        return self.dt
