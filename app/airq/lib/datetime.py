import datetime
import pytz


def local_now() -> datetime.datetime:
    return datetime.datetime.now(tz=pytz.timezone("America/Los_Angeles"))
