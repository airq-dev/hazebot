import datetime
import logging
import time
import typing

from airq.models.sensors import Sensor
from airq.models.zipcodes import Zipcode
from airq.sync.geonames import geonames_sync
from airq.sync.purpleair import purpleair_sync


logger = logging.getLogger(__name__)


def _should_sync_geonames() -> bool:
    now = datetime.datetime.now()
    day = datetime.datetime(year=now.year, month=now.month, day=now.day)
    # Run between midnight and five minutes after midnight
    if (now.timestamp() - day.timestamp()) / 60 < 5:
        return True

    logger.info("Skipping geonames sync because the timestamp is %s", now.timestamp())
    return False


def models_sync(
    force_rebuild_geography: typing.Optional[bool] = None,
    only_if_empty: typing.Optional[bool] = None,
):
    start_ts = time.perf_counter()

    num_zipcodes = Zipcode.query.count()
    if only_if_empty or num_zipcodes == 0:
        force_rebuild_geography = num_zipcodes == 0
    elif force_rebuild_geography is None:
        force_rebuild_geography = _should_sync_geonames()

    if force_rebuild_geography:
        geonames_sync()

    if not only_if_empty or Sensor.query.count() == 0:
        purpleair_sync()

    duration = time.perf_counter() - start_ts
    if duration > 60 * 5:
        log_level = logging.ERROR
    else:
        log_level = logging.INFO
    logger.log(log_level, "Completed models_sync in %s seconds", duration)
