import datetime
import logging
import time
import typing

from airq.models.zipcodes import Zipcode
from airq.sync.geonames import geonames_sync
from airq.sync.purpleair import purpleair_sync


logger = logging.getLogger(__name__)


def _should_sync_geonames() -> bool:
    now = datetime.datetime.now()
    day = datetime.datetime(year=now.year, month=now.month, day=now.day)
    if (now.timestamp() - day.timestamp()) / 60 < 5:
        return True

    if Zipcode.query.count() == 0:
        return True

    logger.info("Skipping geonames sync because the timestamp is %s", now.timestamp())
    return False


def models_sync(force_rebuild_geography: typing.Optional[bool] = None):
    start_ts = time.perf_counter()
    if force_rebuild_geography is None:
        force_rebuild_geography = _should_sync_geonames()
    if force_rebuild_geography:
        geonames_sync()
    purpleair_sync()
    duration = time.perf_counter() - start_ts
    if duration > 60 * 5:
        log_level = logging.ERROR
    else:
        log_level = logging.INFO
    logger.log(log_level, "Completed models_sync in %s seconds", duration)


def test_me():
    logger.exception("test 1")
    raise Exception("test 2")
