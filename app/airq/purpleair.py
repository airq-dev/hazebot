import logging
import requests
import typing

from airq import cache


logger = logging.getLogger(__name__)


class ApiException(Exception):
    pass


def _call_purpleair_api(
    sensor_ids: typing.Set[int],
) -> typing.List[typing.Dict[str, typing.Any]]:
    logger.info(
        "Retrieving pm25 data from purpleair for %s sensors: %s",
        len(sensor_ids),
        sensor_ids,
    )
    try:
        resp = requests.get(
            "https://www.purpleair.com/json?show={}".format(
                "|".join(map(str, sensor_ids))
            )
        )
        resp.raise_for_status()
    except requests.RequestException as e:
        logger.exception(
            "Error retrieving data for sensors %s: %s", sensor_ids, e,
        )
        return []
    else:
        return resp.json().get("results")


def _get_pm25_readings_from_api(sensor_ids: typing.Set[int]) -> typing.Dict[int, float]:
    readings = {}
    dead_sensors = {}

    results = _call_purpleair_api(sensor_ids)
    for r in results:
        if not r.get("ParentID"):
            sensor_id = r["ID"]
            pm25 = float(r.get("PM2_5Value", 0))
            if pm25 <= 0 or pm25 > 500:
                logger.warning(
                    "Marking sensor %s dead because its pm25 is %s", sensor_id, pm25,
                )
                dead_sensors[sensor_id] = True
            else:
                sensor_ids.remove(sensor_id)
                readings[sensor_id] = pm25

    if dead_sensors:
        cache.DEAD.set_many(dead_sensors)

    if sensor_ids:
        # This should be empty now if we've gotten pm25 info for every sensor.
        logger.warning("No results for ids: %s", sensor_ids)

    if readings:
        cache.READINGS.set_many(readings)

    return readings


def get_pm25_readings(sensor_ids: typing.Set[int]) -> typing.Dict[int, float]:
    dead_sensors = cache.DEAD.get_many(sensor_ids)
    sensor_ids -= set(dead_sensors)

    readings = cache.READINGS.get_many(sensor_ids)
    sensor_ids -= set(readings)

    if sensor_ids:
        readings.update(_get_pm25_readings_from_api(sensor_ids))

    return readings
