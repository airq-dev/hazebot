import datetime
import pytz


def now() -> datetime.datetime:
    return datetime.datetime.now()


def local_now() -> datetime.datetime:
    return pytz.timezone("America/Los_Angeles").localize(now())


def timestamp() -> int:
    return int(now().timestamp())
